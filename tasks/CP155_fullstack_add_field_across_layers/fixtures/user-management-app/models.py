"""SQLAlchemy models for user management."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """System user entity mapped to 'sys_user' table."""

    __tablename__ = "sys_user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    display_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(64), nullable=True)
    role = db.Column(db.String(32), default="user")
    avatar_url = db.Column(db.String(512), nullable=True)
    badge_number = db.Column(db.String(32), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "department": self.department,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "badge_number": self.badge_number,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
