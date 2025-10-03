"""
SQLite-compatible models for local development.
Uses String primary keys instead of UUID for SQLite compatibility.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Store(Base):
    __tablename__ = "stores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="store")
    cameras = relationship("Camera", back_populates="store")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="manager")  # store_owner, manager, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    store = relationship("Store", back_populates="users")

    __table_args__ = (
        Index("idx_users_store_email", "store_id", "email"),
    )

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    name = Column(String(255), nullable=False)
    rtsp_url = Column(String(512), nullable=False)
    section = Column(String(255))
    status = Column(String(50), default="offline")  # live, connecting, offline, error
    last_heartbeat_at = Column(DateTime)
    last_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="cameras")

    __table_args__ = (
        Index("idx_cameras_store", "store_id"),
        Index("idx_cameras_status", "status"),
    )

class Invite(Base):
    __tablename__ = "invites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="manager")
    invite_token = Column(String(255), unique=True, nullable=False)
    invited_by = Column(String(36), ForeignKey("users.id"))
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_invites_token", "invite_token"),
        Index("idx_invites_email", "email"),
    )