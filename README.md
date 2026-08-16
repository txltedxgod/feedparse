# feedparse

> Minimalist self-hosted RSS feed aggregator and reader with background fetching.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![APScheduler](https://img.shields.io/badge/Scheduler-APScheduler-orange?style=flat-square)](https://github.com/agronholm/apscheduler)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

`#rss-reader` `#rss-feed` `#news-aggregator` `#fastapi` `#sqlite` `#vanilla-js` `#self-hosted`

---

## Features

- **Feed Management:** Add and remove custom RSS/Atom feeds easily.
- **Automated Fetching:** Background scheduler checks for new articles every 30 minutes.
- **Reading Mode:** Distraction-free reader view with article preview and direct source links.
- **Bookmarks & Read Status:** Star favorite articles and filter by unread/starred status.
- **Manual Sync:** Trigger instant on-demand feed refresh anytime.

## Quick Start

### With Docker

```bash
docker compose up --build
```

### Local Development

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://localhost:8000/static/index.html` in your browser.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/feeds` | Add new RSS feed |
| `GET` | `/api/feeds` | List all subscribed feeds |
| `DELETE` | `/api/feeds/:id` | Remove feed and associated articles |
| `GET` | `/api/articles` | List articles (filters: `feed_id`, `starred`, `unread`) |
| `PATCH` | `/api/articles/:id` | Update read or starred status |
| `POST` | `/api/feeds/refresh` | Trigger immediate refresh across all feeds |

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), SQLite, `feedparser`, `httpx`, `APScheduler`
- **Frontend:** Vanilla JavaScript, Modern CSS
- **Container:** Docker & Docker Compose
