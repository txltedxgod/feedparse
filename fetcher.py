import feedparser
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Feed, Article
import asyncio
import logging

logger = logging.getLogger(__name__)


async def fetch_feed(session: AsyncSession, feed: Feed):
    """Fetch and parse a single RSS feed, saving new articles."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(feed.url)
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f'failed to fetch {feed.url}: {e}')
        return 0

    parsed = feedparser.parse(resp.text)

    if not feed.title and parsed.feed.get('title'):
        feed.title = parsed.feed['title']
    if parsed.feed.get('link'):
        feed.site_url = parsed.feed['link']

    new_count = 0
    for entry in parsed.entries:
        link = entry.get('link', '')
        if not link:
            continue

        # check if article already exists
        existing = await session.execute(
            select(Article).where(Article.url == link, Article.feed_id == feed.id)
        )
        if existing.scalar_one_or_none():
            continue

        pub_date = None
        if entry.get('published_parsed'):
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                pass

        article = Article(
            feed_id=feed.id,
            title=entry.get('title', 'No title'),
            url=link,
            summary=entry.get('summary', ''),
            author=entry.get('author'),
            published=pub_date
        )
        session.add(article)
        new_count += 1

    feed.last_fetched = datetime.utcnow()
    await session.commit()
    logger.info(f'fetched {feed.url}: {new_count} new articles')
    return new_count


async def fetch_all_feeds(session_factory):
    """Fetch all feeds. Called by the scheduler."""
    async with session_factory() as session:
        result = await session.execute(select(Feed))
        feeds = result.scalars().all()
        for feed in feeds:
            await fetch_feed(session, feed)
