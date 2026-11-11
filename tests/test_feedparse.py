import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import app
from database import get_db
from models import Base

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech Digest</title>
    <link>https://example.com</link>
    <item>
      <title>Async SQLite</title>
      <link>https://example.com/posts/1</link>
      <description>&lt;p&gt;Fast SQLite tips&lt;/p&gt;</description>
      <author>dev@example.com</author>
      <pubDate>Wed, 11 Nov 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Unsafe Link</title>
      <link>javascript:alert(1)</link>
      <description>bad</description>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / 'feedparse_test.db'
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_file}')
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_serves_index_and_health(client):
    assert client.get('/health').json() == {'status': 'ok'}
    res = client.get('/')
    assert res.status_code == 200
    assert 'feedparse' in res.text.lower()


@pytest.mark.parametrize(
    'bad_url',
    [
        'file:///etc/passwd',
        'ftp://example.com/feed.xml',
        'http://127.0.0.1:8000/rss',
        'http://localhost/feed.xml',
        'http://169.254.169.254/latest/meta-data',
        'http://10.0.0.5/internal.rss',
    ],
)
def test_rejects_unsafe_or_ssrf_feed_urls(client, bad_url):
    res = client.post('/api/feeds', json={'url': bad_url})
    assert res.status_code == 400


def test_add_fetch_filter_update_and_delete_feed(client, monkeypatch):
    class FakeResponse:
        text = _SAMPLE_RSS

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr('fetcher.httpx.AsyncClient', FakeClient)

    add_res = client.post('/api/feeds', json={'url': 'https://example.com/rss.xml'})
    assert add_res.status_code == 200
    assert add_res.json()['title'] == 'Tech Digest'
    feed_id = add_res.json()['id']

    articles = client.get('/api/articles').json()
    assert len(articles) == 1
    assert articles[0]['title'] == 'Async SQLite'
    assert articles[0]['url'] == 'https://example.com/posts/1'

    art_id = articles[0]['id']
    assert client.patch(f'/api/articles/{art_id}', params={'is_read': True, 'is_starred': True}).status_code == 200

    starred = client.get('/api/articles', params={'starred': True}).json()
    assert len(starred) == 1
    assert client.get('/api/articles', params={'unread': True}).json() == []

    assert client.delete(f'/api/feeds/{feed_id}').status_code == 200
    assert client.get('/api/feeds').json() == []
