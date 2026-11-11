from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Feed(Base):
    __tablename__ = 'feeds'

    id = Column(Integer, primary_key=True)
    title = Column(String(300))
    url = Column(String(500), unique=True, nullable=False)
    site_url = Column(String(500))
    last_fetched = Column(DateTime(timezone=True), nullable=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, nullable=False)
    title = Column(String(500))
    url = Column(String(500))
    summary = Column(Text)
    author = Column(String(200))
    published = Column(DateTime(timezone=True))
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
