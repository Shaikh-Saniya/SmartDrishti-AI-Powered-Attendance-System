"""Initial migration: pgvector extension, all tables, and indexes.

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="teacher", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'teacher')", name="ck_users_role"),
    )

    # Students table
    op.create_table(
        "students",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("roll_number", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("class", sa.String(50), nullable=False),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Student images table
    op.create_table(
        "student_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_path", sa.Text, nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Embeddings table with pgvector
    op.execute("""
        CREATE TABLE embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            embedding vector(512) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    """)

    # Attendance table
    op.create_table(
        "attendance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("time", sa.Time, nullable=False),
        sa.Column("status", sa.String(20), server_default="present", nullable=False),
        sa.Column("marked_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", sa.String(20), server_default="auto", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "date", "subject", name="uq_attendance_student_date_subject"),
        sa.CheckConstraint("status IN ('present', 'absent', 'late')", name="ck_attendance_status"),
        sa.CheckConstraint("source IN ('auto', 'manual')", name="ck_attendance_source"),
    )

    # Unknown faces table with pgvector
    op.execute("""
        CREATE TABLE unknown_faces (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            image_path TEXT NOT NULL,
            embedding vector(512) NOT NULL,
            detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            assigned_to UUID REFERENCES students(id) NULL,
            notes TEXT,
            processed BOOLEAN DEFAULT false NOT NULL
        )
    """)

    # Processing tasks table
    op.create_table(
        "processing_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_processing_tasks_status",
        ),
    )

    # ---------- Indexes ----------
    # Vector indexes for similarity search
    op.execute("""
        CREATE INDEX embeddings_vector_idx ON embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX unknown_faces_vector_idx ON unknown_faces 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
    """)

    # Performance indexes
    op.create_index("idx_attendance_date", "attendance", ["date"])
    op.create_index("idx_attendance_student", "attendance", ["student_id"])
    op.create_index("idx_attendance_subject", "attendance", ["subject"])
    op.create_index("idx_students_roll", "students", ["roll_number"])
    op.create_index("idx_students_class", "students", ["class"])


def downgrade() -> None:
    op.drop_table("processing_tasks")
    op.execute("DROP TABLE IF EXISTS unknown_faces CASCADE")
    op.drop_table("attendance")
    op.execute("DROP TABLE IF EXISTS embeddings CASCADE")
    op.drop_table("student_images")
    op.drop_table("students")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
