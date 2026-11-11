import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session, get_db, init_db
from fetcher import fetch_all_feeds, fetch_feed, validate_feed_url
from models import Article, Feed

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
DbDep = Annotated[AsyncSession, Depends(get_db)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(fetch_all_feeds, 'interval', minutes=30, args=[async_session])
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title='feedparse', lifespan=lifespan)
if STATIC_DIR.is_dir():
    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


class FeedAdd(BaseModel):
    url: str


@app.get('/', include_in_schema=False)
async def serve_index():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/health')
async def health_check():
    return {'status': 'ok'}


@app.post('/api/feeds')
async def add_feed(data: FeedAdd, db: DbDep):
    try:
        clean_url = validate_feed_url(data.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await db.execute(select(Feed).where(Feed.url == clean_url))
    if existing.scalar_one_or_none():
        raise HTTPException(400, 'feed already added')

    feed = Feed(url=clean_url)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)

    await fetch_feed(db, feed)
    return {'id': feed.id, 'title': feed.title, 'url': feed.url}


@app.get('/api/feeds')
async def list_feeds(db: DbDep):
    result = await db.execute(select(Feed).order_by(Feed.added_at.desc()))
    feeds = result.scalars().all()
    return [
        {
            'id': f.id,
            'title': f.title,
            'url': f.url,
            'site_url': f.site_url,
            'last_fetched': f.last_fetched.isoformat() if f.last_fetched else None,
        }
        for f in feeds
    ]


@app.delete('/api/feeds/{feed_id}')
async def remove_feed(feed_id: int, db: DbDep):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404)
    await db.execute(delete(Article).where(Article.feed_id == feed_id))
    await db.delete(feed)
    await db.commit()
    return {'ok': True}


@app.get('/api/articles')
async def list_articles(
    db: DbDep,
    feed_id: int | None = Query(None),
    starred: bool | None = Query(None),
    unread: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(Article)
    if feed_id:
        query = query.where(Article.feed_id == feed_id)
    if starred is not None:
        query = query.where(Article.is_starred == starred)
    if unread:
        query = query.where(Article.is_read.is_(False))

    query = query.order_by(Article.published.desc().nullslast()).offset(offset).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()

    return [
        {
            'id': a.id,
            'feed_id': a.feed_id,
            'title': a.title,
            'url': a.url,
            'summary': a.summary[:300] if a.summary else '',
            'author': a.author,
            'published': a.published.isoformat() if a.published else None,
            'is_read': a.is_read,
            'is_starred': a.is_starred,
        }
        for a in articles
    ]


@app.patch('/api/articles/{article_id}')
async def update_article(
    article_id: int,
    db: DbDep,
    is_read: bool | None = Query(None),
    is_starred: bool | None = Query(None),
):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404)

    if is_read is not None:
        article.is_read = is_read
    if is_starred is not None:
        article.is_starred = is_starred

    await db.commit()
    return {'ok': True}


@app.post('/api/feeds/refresh')
async def refresh_feeds(db: DbDep):
    result = await db.execute(select(Feed))
    feeds = result.scalars().all()
    total = 0
    for feed in feeds:
        total += await fetch_feed(db, feed)
    return {'new_articles': total}
