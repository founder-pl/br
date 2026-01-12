"""
Auth Router - Authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        text("SELECT id, email, full_name, role, is_active FROM auth.users WHERE email = :email"),
        {"email": email}
    )
    user = result.fetchone()
    
    if user is None:
        raise credentials_exception
    
    if not user[4]:  # is_active
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return {
        "id": str(user[0]),
        "email": user[1],
        "full_name": user[2],
        "role": user[3]
    }


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 compatible token login"""
    result = await db.execute(
        text("SELECT id, email, password_hash, is_active FROM auth.users WHERE email = :email"),
        {"email": form_data.username}
    )
    user = result.fetchone()
    
    if not user or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user[3]:  # is_active
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": user[1]})
    
    logger.info("User logged in", email=user[1])
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user exists
    result = await db.execute(
        text("SELECT id FROM auth.users WHERE email = :email"),
        {"email": user.email}
    )
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    import uuid
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(user.password)
    
    await db.execute(
        text("""
        INSERT INTO auth.users (id, email, password_hash, full_name, role, is_active)
        VALUES (:id, :email, :password_hash, :full_name, 'user', true)
        """),
        {
            "id": user_id,
            "email": user.email,
            "password_hash": password_hash,
            "full_name": user.full_name
        }
    )
    
    logger.info("User registered", email=user.email)
    
    return UserResponse(
        id=user_id,
        email=user.email,
        full_name=user.full_name,
        role="user",
        is_active=True,
        created_at=datetime.utcnow()
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info"""
    result = await db.execute(
        text("SELECT id, email, full_name, role, is_active, created_at FROM auth.users WHERE id = :id"),
        {"id": current_user["id"]}
    )
    user = result.fetchone()
    
    return UserResponse(
        id=str(user[0]),
        email=user[1],
        full_name=user[2],
        role=user[3],
        is_active=user[4],
        created_at=user[5]
    )
