from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database import init_db, get_db, async_session
from models import Feed, Article
from fetcher import fetch_feed, fetch_all_feeds
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(fetch_all_feeds, 'interval', minutes=30, args=[async_session])
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title='feedparse', lifespan=lifespan)
app.mount('/static', StaticFiles(directory='static'), name='static')


class FeedAdd(BaseModel):
    url: str


@app.post('/api/feeds')
async def add_feed(data: FeedAdd, db: AsyncSession = Depends(get_db)):
    # check duplicate
    existing = await db.execute(select(Feed).where(Feed.url == data.url))
    if existing.scalar_one_or_none():
        raise HTTPException(400, 'feed already added')

    feed = Feed(url=data.url)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)

    # fetch immediately
    await fetch_feed(db, feed)
    return {'id': feed.id, 'title': feed.title, 'url': feed.url}


@app.get('/api/feeds')
async def list_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).order_by(Feed.added_at.desc()))
    feeds = result.scalars().all()
    return [{
        'id': f.id,
        'title': f.title,
        'url': f.url,
        'site_url': f.site_url,
        'last_fetched': f.last_fetched.isoformat() if f.last_fetched else None
    } for f in feeds]


@app.delete('/api/feeds/{feed_id}')
async def remove_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404)
    # delete articles too
    await db.execute(
        Article.__table__.delete().where(Article.feed_id == feed_id)
    )
    await db.delete(feed)
    await db.commit()
    return {'ok': True}


@app.get('/api/articles')
async def list_articles(
    feed_id: Optional[int] = Query(None),
    starred: Optional[bool] = Query(None),
    unread: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(Article)
    if feed_id:
        query = query.where(Article.feed_id == feed_id)
    if starred is not None:
        query = query.where(Article.is_starred == starred)
    if unread:
        query = query.where(Article.is_read == False)

    query = query.order_by(Article.published.desc().nullslast()).offset(offset).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()

    return [{
        'id': a.id,
        'feed_id': a.feed_id,
        'title': a.title,
        'url': a.url,
        'summary': a.summary[:300] if a.summary else '',
        'author': a.author,
        'published': a.published.isoformat() if a.published else None,
        'is_read': a.is_read,
        'is_starred': a.is_starred
    } for a in articles]


@app.patch('/api/articles/{article_id}')
async def update_article(
    article_id: int,
    is_read: Optional[bool] = Query(None),
    is_starred: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
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
async def refresh_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed))
    feeds = result.scalars().all()
    total = 0
    for feed in feeds:
        total += await fetch_feed(db, feed)
    return {'new_articles': total}
