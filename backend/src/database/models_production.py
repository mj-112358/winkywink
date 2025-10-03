from sqlalchemy import (
    Column, String, BigInteger, Boolean, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Org(Base):
    __tablename__ = "orgs"

    org_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Org(org_id={self.org_id}, name={self.name})>"


class Store(Base):
    __tablename__ = "stores_extended"

    store_id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("orgs.org_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Store(store_id={self.store_id}, org_id={self.org_id}, name={self.name})>"


class Camera(Base):
    __tablename__ = "cameras_extended"

    camera_id = Column(String, primary_key=True)
    store_id = Column(String, ForeignKey("stores_extended.store_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    is_entrance = Column(Boolean, default=False, nullable=False)
    capabilities = Column(ARRAY(String))
    config = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Camera(camera_id={self.camera_id}, store_id={self.store_id}, is_entrance={self.is_entrance}, capabilities={self.capabilities})>"


class EdgeKey(Base):
    __tablename__ = "edge_keys"

    token = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("orgs.org_id", ondelete="CASCADE"), index=True, nullable=False)
    store_id = Column(String, ForeignKey("stores_extended.store_id", ondelete="CASCADE"), index=True, nullable=False)
    camera_id = Column(String, ForeignKey("cameras_extended.camera_id", ondelete="CASCADE"), index=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EdgeKey(token={self.token[:8]}..., camera_id={self.camera_id}, active={self.active})>"


class Event(Base):
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    org_id = Column(String, index=True, nullable=False)
    store_id = Column(String, index=True, nullable=False)
    camera_id = Column(String, index=True, nullable=False)
    person_key = Column(String, index=True)
    type = Column(String, index=True, nullable=False)
    ts = Column(DateTime(timezone=True), index=True, nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_events_event_id', 'event_id', unique=True),
        Index('idx_events_store_ts', 'store_id', 'ts'),
        Index('idx_events_store_type_ts', 'store_id', 'type', 'ts'),
        Index('idx_events_store_camera_person_ts', 'store_id', 'camera_id', 'person_key', 'ts'),
        Index('idx_events_payload_gin', 'payload', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Event(id={self.id}, event_id={self.event_id[:8]}..., type={self.type}, store_id={self.store_id}, ts={self.ts})>"


class Aggregation(Base):
    __tablename__ = "aggregations"

    org_id = Column(String, primary_key=True)
    store_id = Column(String, primary_key=True)
    metric = Column(String, primary_key=True)
    period_start = Column(DateTime(timezone=True), primary_key=True)
    granularity = Column(String, default="hour")
    payload = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Aggregation(store_id={self.store_id}, metric={self.metric}, period={self.period_start})>"
