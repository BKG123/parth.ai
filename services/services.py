from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Base

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
