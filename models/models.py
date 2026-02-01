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
    Computed,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    meta_data = Column(JSONB)


class GoalStatus(enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    abandoned = "abandoned"


class MessageStatus(enum.Enum):
    pending = "pending"
    sent = "sent"
    cancelled = "cancelled"


class SkillCreatedBy(enum.Enum):
    system = "system"
    agent = "agent"


class MessageRole(enum.Enum):
    user = "user"
    assistant = "assistant"


class User(BaseModel):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    timezone = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    goals = relationship("Goal", back_populates="user")
    scheduled_messages = relationship("ScheduledMessage", back_populates="user")
    skills = relationship("Skill", back_populates="creator")
    messages = relationship("Message", back_populates="user")


class UserPreference(BaseModel):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    agent_data = Column(JSONB)

    # Relationships
    user = relationship("User", back_populates="preferences")


class Goal(BaseModel):
    __tablename__ = "goals"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    status = Column(Enum(GoalStatus), nullable=False, default=GoalStatus.active)

    # Relationships
    user = relationship("User", back_populates="goals")
    goal_data = relationship("GoalData", back_populates="goal", uselist=False)
    scheduled_messages = relationship("ScheduledMessage", back_populates="goal")
    goal_skills = relationship("GoalSkill", back_populates="goal")
    messages = relationship("Message", back_populates="goal")


class GoalData(BaseModel):
    __tablename__ = "goal_data"

    goal_id = Column(Integer, ForeignKey("goals.id"), unique=True, nullable=False)
    agent_data = Column(JSONB)

    # Relationships
    goal = relationship("Goal", back_populates="goal_data")


class ScheduledMessage(BaseModel):
    __tablename__ = "scheduled_messages"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    scheduled_for = Column(DateTime, nullable=False)
    message_content = Column(Text, nullable=False)
    status = Column(Enum(MessageStatus), nullable=False, default=MessageStatus.pending)

    # Relationships
    user = relationship("User", back_populates="scheduled_messages")
    goal = relationship("Goal", back_populates="scheduled_messages")


class Skill(BaseModel):
    __tablename__ = "skills"

    name = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    skill_prompt = Column(Text, nullable=False)
    skill_metadata = Column(JSONB)
    created_by_type = Column(Enum(SkillCreatedBy), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # Full-text search vector (computed column for PostgreSQL)
    search_vector = Column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(name, '') || ' ' || coalesce(title, '') || ' ' || coalesce(description, ''))"
        ),
    )

    # Relationships
    creator = relationship("User", back_populates="skills")
    goal_skills = relationship("GoalSkill", back_populates="skill")


class GoalSkill(BaseModel):
    __tablename__ = "goal_skills"

    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    customizations = Column(JSONB)

    # Relationships
    goal = relationship("Goal", back_populates="goal_skills")
    skill = relationship("Skill", back_populates="goal_skills")


class Message(BaseModel):
    __tablename__ = "messages"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    telegram_message_id = Column(BigInteger, nullable=True)

    # Relationships
    user = relationship("User", back_populates="messages")
    goal = relationship("Goal", back_populates="messages")
