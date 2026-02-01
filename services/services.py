from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Base, Skill, Message, User
from database import AsyncSessionLocal

ModelType = TypeVar("ModelType", bound=Base)


class BaseCRUD(Generic[ModelType]):
    """Base CRUD operations for all models"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        """Create a new record"""
        obj = self.model(**kwargs)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get a record by ID"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by(self, db: AsyncSession, **filters) -> Optional[ModelType]:
        """Get a single record by filters"""
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters
    ) -> List[ModelType]:
        """Get all records with optional filters and pagination"""
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, id: int, **kwargs) -> Optional[ModelType]:
        """Update a record by ID"""
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    async def update_by(
        self, db: AsyncSession, filters: Dict[str, Any], **kwargs
    ) -> int:
        """Update records by filters, returns count of updated records"""
        stmt = update(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.values(**kwargs)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def delete(self, db: AsyncSession, id: int) -> bool:
        """Delete a record by ID"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def delete_by(self, db: AsyncSession, **filters) -> int:
        """Delete records by filters, returns count of deleted records"""
        stmt = delete(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def count(self, db: AsyncSession, **filters) -> int:
        """Count records with optional filters"""
        query = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return result.scalar()

    async def exists(self, db: AsyncSession, **filters) -> bool:
        """Check if a record exists with given filters"""
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        query = query.limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


class SkillCRUD(BaseCRUD[Skill]):
    """Extended CRUD operations for Skills with search functionality"""

    async def search(
        self, db: AsyncSession, query: str, limit: int = 10
    ) -> List[Skill]:
        """
        Search skills using PostgreSQL full-text search with ILIKE fallback.

        First attempts full-text search which handles:
        - Word stemming (e.g., "running" matches "run")
        - Word order independence
        - Common word filtering

        Falls back to ILIKE pattern matching if no results found.
        """
        # Try full-text search first
        fts_stmt = (
            select(self.model)
            .where(self.model.is_active)
            .where(
                self.model.search_vector.op("@@")(
                    func.plainto_tsquery("english", query)
                )
            )
            .order_by(
                func.ts_rank(
                    self.model.search_vector, func.plainto_tsquery("english", query)
                ).desc(),
                self.model.usage_count.desc(),
            )
            .limit(limit)
        )
        result = await db.execute(fts_stmt)
        skills = list(result.scalars().all())

        # If no results, fall back to ILIKE pattern matching
        if not skills:
            search_pattern = f"%{query}%"
            ilike_stmt = (
                select(self.model)
                .where(self.model.is_active)
                .where(
                    or_(
                        self.model.name.ilike(search_pattern),
                        self.model.title.ilike(search_pattern),
                        self.model.description.ilike(search_pattern),
                    )
                )
                .order_by(self.model.usage_count.desc())
                .limit(limit)
            )
            result = await db.execute(ilike_stmt)
            skills = list(result.scalars().all())

        return skills


class MessageCRUD(BaseCRUD[Message]):
    """Extended CRUD operations for Messages"""

    async def get_by_user(
        self, db: AsyncSession, user_id: int, limit: int = 100
    ) -> List[Message]:
        """Get messages for a specific user"""
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


class UserCRUD(BaseCRUD[User]):
    """Extended CRUD operations for Users"""

    async def get_or_create_by_telegram_id(
        self, db: AsyncSession, telegram_id: int
    ) -> User:
        """Get or create a user by telegram_id"""
        user = await self.get_by(db, telegram_id=telegram_id)
        if not user:
            user = await self.create(db, telegram_id=telegram_id)
        return user


if __name__ == "__main__":
    import asyncio
    from models.models import User

    # create a new user
    user = User(telegram_id=1234567890)
    user_crud = BaseCRUD(User)

    async def main():
        async with AsyncSessionLocal() as db:
            user = await user_crud.create(db, telegram_id=1234567890)
            print(f"User created with ID: {user.id}")

    asyncio.run(main())
