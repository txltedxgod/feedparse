# feedparse

Minimal self-hosted RSS feed aggregator. Add feeds, read articles in a clean dark UI.

## Features

- Add/remove RSS feeds
- Auto-fetches new articles every 30 min
- Mark as read, star articles
- Filter by feed, unread, starred
- Manual refresh button
- Dark UI, no dependencies on frontend

## Setup

```bash
# docker
docker compose up --build

# or local
pip install -r requirements.txt
uvicorn app:app --reload
```

Then open http://localhost:8000/static/index.html

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/feeds | Add new feed |
| GET | /api/feeds | List feeds |
| DELETE | /api/feeds/:id | Remove feed |
| GET | /api/articles | List articles (query: feed_id, starred, unread) |
| PATCH | /api/articles/:id | Update read/star status |
| POST | /api/feeds/refresh | Manually refresh all feeds |

## Tech

- FastAPI + SQLAlchemy 2.0 (async)
- feedparser + httpx for RSS fetching
- APScheduler for background jobs
- SQLite
- Vanilla JS frontend
