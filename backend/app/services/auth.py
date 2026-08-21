"""Focused authentication and user persistence operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User


def normalize_email(email: str) -> str:
    """Normalize email consistently for lookup and creation."""

    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by normalized email."""

    return db.scalar(select(User).where(User.email == normalize_email(email)))


def get_user_by_id(db: Session, user_id) -> User | None:
    """Fetch a user by primary key."""

    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return an active user for valid credentials, otherwise None."""

    user = get_user_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def create_admin_user(db: Session, name: str, email: str, password: str) -> User:
    """Create one active admin with a hashed password."""

    normalized_email = normalize_email(email)
    if not name.strip():
        raise ValueError("Name is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if get_user_by_email(db, normalized_email) is not None:
        raise ValueError("A user with this email already exists.")

    user = User(
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("A user with this email already exists.") from exc
    db.refresh(user)
    return user
