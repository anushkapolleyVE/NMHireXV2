from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.get(User, user_id)

    if not user or not user.is_active:
        raise credentials_exception

    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:

    if user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user


def require_recruiter(
    user: User = Depends(get_current_user),
) -> User:

    if user.role != "RECRUITER":
        raise HTTPException(
            status_code=403,
            detail="Recruiter access required",
        )

    return user