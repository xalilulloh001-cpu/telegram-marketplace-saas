"""Declarative base for SQLAlchemy models. Business models are added in Phase 2."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
