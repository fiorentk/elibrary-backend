from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import ForeignKey, CheckConstraint
from datetime import datetime
from typing import List, Optional
import uuid

class Users(SQLModel, table=True):
    __tablename__ = "users"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            name="uid",
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    username: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="username",
            unique=True,
            nullable=False
        )
    )
    password: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="password",
            nullable=False
        )
    )
    role: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="role",
            nullable=False,
            server_default="user"
        )
    )
    name: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="name",
            nullable=False
        )
    )
    address: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="address",
            nullable=False
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="created_at",
            default=datetime.utcnow,
            nullable=False
        )
    )

    # Relationship to Books and Transactions
    books: List["Books"] = Relationship(back_populates="created_by_user")
    admin_transactions: List["Transactions"] = Relationship(
        back_populates="admin_user",
        sa_relationship_kwargs={"foreign_keys": "Transactions.admin_id"})

    user_requests: List["Requests"] = Relationship(
        back_populates="request_user",
        sa_relationship_kwargs={"foreign_keys": "Requests.user_id"})

    user_review: List["BookReviews"] = Relationship(back_populates="review_user")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="valid_role_check"),
    )

class Books(SQLModel, table=True):
    __tablename__ = "books"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            name="uid",
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    title: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="title",
            nullable=False
        )
    )
    author: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="author",
            nullable=False
        )
    )
    category: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="category",
            nullable=False,
        )
    )
    availability: bool = Field(
        sa_column=Column(
            pg.BOOLEAN,
            name="availability",
            nullable=False,
            default=True
        )
    )
    summary: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="summary",
            nullable=True  # Allowing NULL for optional fields
        )
    )
    admin_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("users.uid"),
            nullable=False
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="created_at",
            default=datetime.utcnow,
            nullable=False
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="updated_at",
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )
    )

    # Relationships
    created_by_user: "Users" = Relationship(back_populates="books")
    borrow_request: List["Requests"] = Relationship(back_populates="borrowed_book")
    book_review: List["BookReviews"] = Relationship(back_populates="review_book")

class Requests(SQLModel, table=True):
    __tablename__ = "requests"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            name="uid",
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("users.uid"),
            nullable=False
        )
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("books.uid"),
            nullable=False
        )
    )
    requested_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="requested_at",
            default=datetime.utcnow,
            nullable=False
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="updated_at",
            default=datetime.utcnow,
            nullable=False
        )
    )
    duration: int= Field(
        sa_column=Column(
            pg.INTEGER,
            name="duration",
            nullable=False
        )
    )
    status: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="status",
            nullable=False,
            default="pending",
        )
    )
    description: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="description",
            nullable=True,
        )
    )

    # Relationship to borrower user
    request_user: "Users" = Relationship(
        back_populates="user_requests",
        sa_relationship_kwargs={"foreign_keys": "Requests.user_id"}
    )
    borrowed_book: "Books" = Relationship(back_populates="borrow_request")
    accepted_request: "Transactions" = Relationship(back_populates="transaction_from_request")

class Transactions(SQLModel, table=True):
    __tablename__ = "transactions"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            name="uid",
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    admin_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("users.uid"),
            nullable=False
        )
    )
    request_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("requests.uid"),
            nullable=False
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="created_at",
            default=datetime.utcnow,
            nullable=True
        )
    )
    due_date: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="due_date",
            nullable=False
        )
    )
    returned_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="returned_at",
            nullable=True  # Allowing NULL for unreturned books
        )
    )
    is_overdue: bool = Field(
        sa_column=Column(
            pg.BOOLEAN,
            name="is_overdue",
            default=False,
            nullable=False
        )
    )

    # Relationships
    admin_user: "Users" = Relationship(
        back_populates="admin_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transactions.admin_id"}
    )
    transaction_from_request: "Requests" = Relationship(back_populates="accepted_request")


class BookReviews(SQLModel, table=True):
    __tablename__ = "reviews"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            name="uid",
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("users.uid"),
            nullable=False
        )
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("books.uid"),
            nullable=False
        )
    )
    rating: float = Field(
        sa_column=Column(
            pg.NUMERIC(precision=2, scale=1),  # Allows for numbers like 9.9, 10.0, etc.
            name="rating",
            nullable=False
        )
    )
    description: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            name="description",
            nullable=True  # Allowing NULL for optional fields
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="created_at",
            default=datetime.utcnow,
            nullable=False
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            name="updated_at",
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )
    )


    # Relationships
    review_user: "Users" = Relationship(back_populates="user_review")
    review_book: "Books" = Relationship(back_populates="book_review")