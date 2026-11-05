from app.api.v1.agents import router
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse
)

from app.api.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

#Register
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    request: UserRegister,
    db: Session = Depends(get_db)
):

     existing_user = db.query(User).filter(
        User.email == request.email
     ).first()

     if existing_user:

        raise HTTPException(
            status_code = 409,
            detail = "Email already registered"
        )
     user = User(
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        auth_provider="email"
     )

     db.add(user)
     db.commit()
     db.refresh(user)

     return user

# LOGIN
@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    request: UserLogin,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user or not user.password_hash:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(
        request.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# CURRENT USER
@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):
  return current_user