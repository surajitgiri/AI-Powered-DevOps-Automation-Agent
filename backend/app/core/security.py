from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.core.config import settings

password_hash = PasswordHash.recommended()

# Password hashing
def hash_password(password: str) -> str:
    return password_hash.hash(password)

# Verify password
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )

# Generate JWT access token
def create_access_token(user_id: str):

    expire = datetime.now(timezone.utc) + timedelta(
        minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


# Verify JWT access token
def verify_access_token(token: str):

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            return None
        
        return user_id
    
    except jwt.InvalidTokenError:

        return None