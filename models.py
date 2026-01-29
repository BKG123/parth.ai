from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class GoalStatus(enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    abandoned = "abandoned"


class MessageStatus(enum.Enum):
    pending = "pending"
    sent = "sent"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    timezone = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    goals = relationship("Goal", back_populates="user")
    scheduled_messages = relationship("ScheduledMessage", back_populates="user")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    agent_data = Column(JSONB)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="preferences")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    status = Column(Enum(GoalStatus), nullable=False, default=GoalStatus.active)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="goals")
    goal_data = relationship("GoalData", back_populates="goal", uselist=False)
    scheduled_messages = relationship("ScheduledMessage", back_populates="goal")


class GoalData(Base):
    __tablename__ = "goal_data"

    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), unique=True, nullable=False)
    agent_data = Column(JSONB)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    goal = relationship("Goal", back_populates="goal_data")


class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    scheduled_for = Column(DateTime, nullable=False)
    message_content = Column(Text, nullable=False)
    status = Column(Enum(MessageStatus), nullable=False, default=MessageStatus.pending)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="scheduled_messages")
    goal = relationship("Goal", back_populates="scheduled_messages")
