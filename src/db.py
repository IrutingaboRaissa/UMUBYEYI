"""
Umubyeyi - analytics & feedback datastore (privacy-by-design).

Stores ONLY non-sensitive, anonymous signals: a per-session random id, detected language,
response mode, whether the answer was grounded, retrieval score, latency, timestamps, and
thumbs feedback. It never stores message text, names, or anything identifying — the actual
conversation lives on the user's device (browser localStorage), not here.

One codebase, two backends via SQLAlchemy:
  - Production: Postgres  (set DATABASE_URL, e.g. a free Neon/Supabase instance)
  - Local/dev: SQLite     (falls back to a local umubyeyi_analytics.db file, zero setup)

Everything is guarded: if the driver or the database is unavailable, the functions become
no-ops and the app keeps working.
"""
import os
import datetime
from pathlib import Path

DB_OK = False
INIT_ERROR = None
BACKEND = None

try:
    from sqlalchemy import (create_engine, Column, Integer, String, Float, Boolean,
                            DateTime, func)
    from sqlalchemy.orm import declarative_base, sessionmaker

    _url = os.environ.get("DATABASE_URL", "").strip()
    # A copied example placeholder is not a configured database.
    if "user:password@host/" in _url:
        _url = ""
    if _url:
        # Heroku/Neon sometimes hand out the legacy "postgres://" scheme; SQLAlchemy wants "postgresql://"
        if _url.startswith("postgres://"):
            _url = _url.replace("postgres://", "postgresql://", 1)
        BACKEND = "postgres"
    else:
        _url = f"sqlite:///{Path(__file__).resolve().parents[1] / 'umubyeyi_analytics.db'}"
        BACKEND = "sqlite"

    _connect_args = {"check_same_thread": False} if BACKEND == "sqlite" else {"connect_timeout": 3}
    _engine = create_engine(_url, pool_pre_ping=True, connect_args=_connect_args)
    Base = declarative_base()

    class Event(Base):
        """One row per assistant answer (anonymous)."""
        __tablename__ = "events"
        id = Column(Integer, primary_key=True)
        session_id = Column(String(40), index=True)
        language = Column(String(4))
        mode = Column(String(20))          # generative | safety | unavailable
        grounded = Column(Boolean)
        top_sim = Column(Float)            # best retrieval cosine similarity
        latency_ms = Column(Integer)
        created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    class Feedback(Base):
        """A thumbs up/down on an answer (anonymous)."""
        __tablename__ = "feedback"
        id = Column(Integer, primary_key=True)
        session_id = Column(String(40), index=True)
        rating = Column(Integer)           # +1 helpful, -1 not helpful
        language = Column(String(4))
        mode = Column(String(20))
        created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    class Action(Base):
        """An anonymous chat-management action: new_chat | rename | delete (no content)."""
        __tablename__ = "actions"
        id = Column(Integer, primary_key=True)
        session_id = Column(String(40), index=True)
        action = Column(String(20))
        created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    DB_OK = True
except Exception as e:                     # missing driver, bad URL, unreachable db -> no-op mode
    INIT_ERROR = f"{type(e).__name__}: {e}"


def log_event(session_id, language, mode, grounded, top_sim, latency_ms):
    if not DB_OK:
        return
    try:
        s = _Session()
        s.add(Event(session_id=session_id, language=language, mode=mode, grounded=bool(grounded),
                    top_sim=float(top_sim or 0.0), latency_ms=int(latency_ms)))
        s.commit(); s.close()
    except Exception:
        pass


def log_feedback(session_id, rating, language, mode):
    if not DB_OK:
        return
    try:
        s = _Session()
        s.add(Feedback(session_id=session_id, rating=int(rating), language=language, mode=mode))
        s.commit(); s.close()
    except Exception:
        pass


def log_action(session_id, action):
    """Record an anonymous chat-management action (new_chat | rename | delete). No content stored."""
    if not DB_OK:
        return
    try:
        s = _Session()
        s.add(Action(session_id=session_id, action=str(action)[:20]))
        s.commit(); s.close()
    except Exception:
        pass


def insights():
    """Aggregate metrics for the in-app dashboard (returns None if the db is unavailable)."""
    if not DB_OK:
        return None
    try:
        s = _Session()
        total = s.query(func.count(Event.id)).scalar() or 0
        by_lang = dict(s.query(Event.language, func.count(Event.id)).group_by(Event.language).all())
        by_mode = dict(s.query(Event.mode, func.count(Event.id)).group_by(Event.mode).all())
        grounded = s.query(func.count(Event.id)).filter(Event.grounded.is_(True)).scalar() or 0
        avg_latency = s.query(func.avg(Event.latency_ms)).scalar()
        fb_total = s.query(func.count(Feedback.id)).scalar() or 0
        fb_pos = s.query(func.count(Feedback.id)).filter(Feedback.rating > 0).scalar() or 0
        sessions = s.query(func.count(func.distinct(Event.session_id))).scalar() or 0
        by_action = dict(s.query(Action.action, func.count(Action.id)).group_by(Action.action).all())
        s.close()
        return {
            "backend": BACKEND,
            "answers": total,
            "sessions": sessions,
            "by_language": by_lang,
            "by_mode": by_mode,
            "grounded_rate": (grounded / total) if total else 0.0,
            "avg_latency_ms": int(avg_latency) if avg_latency else 0,
            "feedback_total": fb_total,
            "feedback_positive_rate": (fb_pos / fb_total) if fb_total else None,
            "by_action": by_action,
        }
    except Exception:
        return None
