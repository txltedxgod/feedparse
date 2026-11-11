import ipaddress
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Article, Feed

logger = logging.getLogger(__name__)
_BLOCKED_HOSTS = {'localhost', 'localhost.localdomain'}


def validate_feed_url(raw_url: str) -> str:
    url = raw_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('feed URL must use http or https with a valid host')

    host = parsed.hostname.lower().rstrip('.')
    if host in _BLOCKED_HOSTS or host.endswith(('.localhost', '.local')):
        raise ValueError('local hostnames are not permitted')

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise ValueError('private or internal IP addresses are not permitted')
    return url


def _safe_http_link(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    candidate = raw_url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme in ('http', 'https') and parsed.hostname:
        return candidate
    return None


async def fetch_feed(session: AsyncSession, feed: Feed) -> int:
    """Fetch and parse a single RSS feed, saving new articles."""
    try:
        safe_url = validate_feed_url(feed.url)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(safe_url)
            resp.raise_for_status()
    except (ValueError, httpx.HTTPError) as exc:
        logger.warning('failed to fetch %s: %s', feed.url, exc)
        return 0

    parsed = feedparser.parse(resp.text)

    if not feed.title and parsed.feed.get('title'):
        feed.title = parsed.feed['title']
    safe_site = _safe_http_link(parsed.feed.get('link'))
    if safe_site:
        feed.site_url = safe_site

    new_count = 0
    for entry in parsed.entries:
        link = _safe_http_link(entry.get('link', ''))
        if not link:
            continue

        existing = await session.execute(
            select(Article).where(Article.url == link, Article.feed_id == feed.id)
        )
        if existing.scalar_one_or_none():
            continue

        pub_date = None
        if entry.get('published_parsed'):
            try:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                pub_date = None

        article = Article(
            feed_id=feed.id,
            title=entry.get('title', 'No title'),
            url=link,
            summary=entry.get('summary', ''),
            author=entry.get('author'),
            published=pub_date,
        )
        session.add(article)
        new_count += 1

    feed.last_fetched = datetime.now(UTC)
    await session.commit()
    logger.info('fetched %s: %d new articles', feed.url, new_count)
    return new_count


async def fetch_all_feeds(session_factory):
    """Fetch all feeds. Called by the scheduler."""
    async with session_factory() as session:
        result = await session.execute(select(Feed))
        feeds = result.scalars().all()
        for feed in feeds:
            await fetch_feed(session, feed)
