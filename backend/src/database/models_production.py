from sqlalchemy import (
    Column, String, BigInteger, Integer, Boolean, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Org(Base):
    __tablename__ = "orgs"

    org_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Org(org_id={self.org_id}, name={self.name})>"


class Store(Base):
    __tablename__ = "stores_extended"

    store_id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("orgs.org_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Store(store_id={self.store_id}, org_id={self.org_id}, name={self.name})>"


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("orgs.org_id", ondelete="CASCADE"), index=True, nullable=False)
    store_id = Column(String, ForeignKey("stores_extended.store_id", ondelete="CASCADE"), index=True, nullable=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email}, org_id={self.org_id})>"


class Camera(Base):
    __tablename__ = "cameras_extended"

    camera_id = Column(String, primary_key=True)
    store_id = Column(String, ForeignKey("stores_extended.store_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    is_entrance = Column(Boolean, default=False, nullable=False)
    rtsp_url = Column(String, nullable=True)
    capabilities = Column(JSON)  # Store as JSON array for SQLite compatibility
    config = Column(JSON, nullable=False, default='{}')
    last_heartbeat_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Camera(camera_id={self.camera_id}, store_id={self.store_id}, is_entrance={self.is_entrance}, is_active={self.is_active})>"


class EdgeKey(Base):
    __tablename__ = "edge_keys"

    key = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("orgs.org_id", ondelete="CASCADE"), index=True, nullable=False)
    store_id = Column(String, ForeignKey("stores_extended.store_id", ondelete="CASCADE"), index=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EdgeKey(key={self.key[:8]}..., store_id={self.store_id}, active={self.active})>"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    org_id = Column(String, index=True, nullable=False)
    store_id = Column(String, index=True, nullable=False)
    camera_id = Column(String, index=True, nullable=False)
    person_key = Column(String, index=True)
    type = Column(String, index=True, nullable=False)
    ts = Column(DateTime, index=True, nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Event(id={self.id}, event_id={self.event_id[:8] if len(self.event_id) > 8 else self.event_id}..., type={self.type}, store_id={self.store_id}, ts={self.ts})>"


class Aggregation(Base):
    __tablename__ = "aggregations"

    org_id = Column(String, primary_key=True)
    store_id = Column(String, primary_key=True)
    metric = Column(String, primary_key=True)
    period_start = Column(DateTime, primary_key=True)
    granularity = Column(String, default="hour")
    payload = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Aggregation(store_id={self.store_id}, metric={self.metric}, period={self.period_start})>"
