from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.modules.auth.models import Company, Site, User, RefreshToken, AuditLog
from app.modules.auth.schemas import UserOut


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, name=u.name,
        role=u.role, company_id=u.company_id, site_id=u.site_id,
    )


def _audit(db: Session, user_id: str | None, action: str, detail: str = ""):
    db.add(AuditLog(id=f"aud-{uuid4().hex[:12]}", user_id=user_id, action=action, detail=detail))
    db.commit()


def create_refresh_token(user_id: str, db: Session) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    token_str = str(uuid4()) + str(uuid4())
    db.add(RefreshToken(
        id=f"rt-{uuid4().hex[:12]}",
        user_id=user_id,
        token=token_str,
        expires_at=expire.replace(tzinfo=None),
        revoked=False,
    ))
    db.commit()
    return token_str


def register_user(db: Session, company_name: str, name: str, email: str, password: str):
    if db.query(User).filter(User.email == email.lower()).first():
        raise HTTPException(400, detail="Cet email est déjà utilisé.")

    company_id = f"co-{uuid4().hex[:10]}"
    db.add(Company(id=company_id, name=company_name.strip()))

    site_id = f"site-{uuid4().hex[:8]}"
    db.add(Site(id=site_id, name="Site principal", company_id=company_id))

    user = User(
        id=f"user-{uuid4().hex[:10]}",
        email=email.lower().strip(),
        name=name.strip(),
        password_hash=hash_password(password),
        role="ADMIN",
        company_id=company_id,
        site_id=site_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access = create_access_token(user.id, user.email, user.role, user.company_id)
    refresh = create_refresh_token(user.id, db)
    _audit(db, user.id, "REGISTER", company_name)
    return access, refresh, _user_out(user)


def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        _audit(db, None, "LOGIN_FAILED", email.lower())
        raise HTTPException(401, detail="Email ou mot de passe incorrect.")
    if not user.is_active:
        raise HTTPException(403, detail="Compte désactivé.")

    access = create_access_token(user.id, user.email, user.role, user.company_id)
    refresh = create_refresh_token(user.id, db)
    _audit(db, user.id, "LOGIN", "ok")
    return access, refresh, _user_out(user)