from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserOut,
)
from app.modules.auth import service

router = APIRouter(prefix="/api/auth", tags=["Auth"])
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(401, detail="Non authentifié")
    payload = decode_access_token(creds.credentials)
    user = db.query(User).filter(User.id == payload.get("sub"), User.is_active == True).first()
    if not user:
        raise HTTPException(401, detail="Utilisateur introuvable")
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    access, refresh, user = service.register_user(
        db, body.company_name, body.name, body.email, body.password
    )
    return TokenResponse(access_token=access, refresh_token=refresh, user=user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    access, refresh, user = service.login_user(db, body.email, body.password)
    return TokenResponse(access_token=access, refresh_token=refresh, user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        company_id=user.company_id,
        site_id=user.site_id,
    )