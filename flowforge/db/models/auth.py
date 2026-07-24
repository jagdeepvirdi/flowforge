from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _CASCADE, _FF_PROJECTS_ID, _utcnow, _uuid, db


class User(db.Model):
    __tablename__ = 'ff_users'
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name='ck_user_role'),
    )

    id               = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username         = Column(String(100), nullable=False, unique=True)
    password_hash    = Column(String(255), nullable=False)
    role             = Column(String(20), nullable=False, default='editor')
    email            = Column(String(255), index=True)  # optional — for password reset
    # MFA (TOTP) — secret and backup codes stored AES-256 encrypted
    mfa_secret       = Column(Text)
    mfa_enabled      = Column(Boolean, nullable=False, default=False)
    mfa_backup_codes = Column(Text)                    # encrypted JSON list of remaining codes
    # SSO — provider ('google' | 'microsoft' | 'saml') and matched email
    sso_provider     = Column(String(20))
    sso_email        = Column(String(255), index=True)
    created_at       = Column(DateTime(timezone=True), default=_utcnow)

    project_memberships = relationship('ProjectMember', back_populates='user', cascade=_CASCADE)


class ProjectMember(db.Model):
    """Team-scoped project access — non-admin users can only see/edit resources
    in projects they're a member of. Admins bypass this check everywhere
    (see flowforge/api/project_access.py)."""
    __tablename__ = 'ff_project_members'
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete='CASCADE'), nullable=False, index=True)
    user_id    = Column(UUID(as_uuid=False), ForeignKey('ff_users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship('Project', back_populates='members')
    user    = relationship('User', back_populates='project_memberships')


class TokenBlocklist(db.Model):
    """Revoked JWT IDs. Entries older than their expires_at are dead weight and can be pruned."""
    __tablename__ = 'ff_token_blocklist'

    jti        = Column(String(36), primary_key=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(db.Model):
    """Single-use password reset tokens, valid for 1 hour."""
    __tablename__ = 'ff_password_reset_tokens'

    token      = Column(String(64),              primary_key=True)
    user_id    = Column(UUID(as_uuid=False),      ForeignKey('ff_users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True),  nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True),  nullable=False)
    used_at    = Column(DateTime(timezone=True))
