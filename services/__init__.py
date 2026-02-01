from services.services import BaseCRUD, SkillCRUD
from models.models import (
    User,
    UserPreference,
    Goal,
    GoalData,
    ScheduledMessage,
    Skill,
    GoalSkill,
    Message,
)

# CRUD instances for each model
user_crud = BaseCRUD(User)
user_preference_crud = BaseCRUD(UserPreference)
goal_crud = BaseCRUD(Goal)
goal_data_crud = BaseCRUD(GoalData)
scheduled_message_crud = BaseCRUD(ScheduledMessage)
skill_crud = SkillCRUD(Skill)
goal_skill_crud = BaseCRUD(GoalSkill)
message_crud = BaseCRUD(Message)

__all__ = [
    "BaseCRUD",
    "SkillCRUD",
    "user_crud",
    "user_preference_crud",
    "goal_crud",
    "goal_data_crud",
    "scheduled_message_crud",
    "skill_crud",
    "goal_skill_crud",
    "message_crud",
]
