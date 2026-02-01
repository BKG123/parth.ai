"""add_fulltext_search_to_skills

Revision ID: bccad34fbe5f
Revises: b12bb42c53a0
Create Date: 2026-02-01 22:07:19.943124

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bccad34fbe5f"
down_revision: Union[str, Sequence[str], None] = "b12bb42c53a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search vector and GIN index to skills table."""
    # Add computed search_vector column
    op.execute("""
        ALTER TABLE skills 
        ADD COLUMN search_vector tsvector 
        GENERATED ALWAYS AS (
            to_tsvector('english', 
                coalesce(name, '') || ' ' || 
                coalesce(title, '') || ' ' || 
                coalesce(description, '')
            )
        ) STORED
    """)

    # Create GIN index for fast full-text search
    op.create_index(
        "idx_skills_search_vector", "skills", ["search_vector"], postgresql_using="gin"
    )


def downgrade() -> None:
    """Remove full-text search vector and index from skills table."""
    # Drop the GIN index
    op.drop_index("idx_skills_search_vector", table_name="skills")

    # Drop the search_vector column
    op.drop_column("skills", "search_vector")
