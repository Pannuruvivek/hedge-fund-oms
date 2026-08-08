from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, RoleName
from ..schemas import UserCreate, UserOut, Token
from ..auth import hash_password, verify_password, create_access_token, get_current_user, require_roles
from .. import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db),
             # Only an existing ADMIN may create new users, except for bootstrapping
             # the very first user when the user table is empty.
             ):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    user_count = db.query(User).count()
    role = payload.role
    if user_count == 0:
        role = RoleName.ADMIN  # first user bootstraps as admin

    user = User(username=payload.username, hashed_password=hash_password(payload.password), role=role)
    db.add(user)
    db.flush()
    audit.record(db, user, "USER_REGISTER", entity_type="User", entity_id=user.id, detail=f"role={role.value}")
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    audit.record(db, user, "LOGIN", entity_type="User", entity_id=user.id)
    db.commit()
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db),
               _: User = Depends(require_roles(RoleName.ADMIN))):
    return db.query(User).all()
