from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.enums import UserRole, AuditAction, AuditResult
from app.schemas.user import UserCreate, UserLogin, UserOut, TokenResponse
from app.middleware.auth_deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Registers a new user account.
    
    Security:
    - Verifies uniqueness of email and username.
    - Hashes password using Argon2id.
    - Default public registrations are assigned VIEWER or OWNER; ADMIN cannot be self-assigned.
    - Emits a cryptographic audit log record.
    """
    # Check if email or username already exists
    existing_user = db.query(User).filter(
        or_(User.email == user_in.email, User.username == user_in.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email or username already exists."
        )

    # Disallow self-registration as ADMIN
    assigned_role = user_in.role if user_in.role in (UserRole.OWNER, UserRole.VIEWER) else UserRole.VIEWER

    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=assigned_role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log registration
    client_ip = request.client.host if request.client else "unknown"
    AuditService.log_event(
        db=db,
        action=AuditAction.USER_REGISTER,
        result=AuditResult.SUCCESS,
        actor_id=user.id,
        details={"ip": client_ip, "username": user.username, "role": user.role.value}
    )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticates a user via username or email and returns a signed JWT access token.
    
    Security:
    - Protects against user enumeration by returning identical error messages.
    - Rejects inactive or suspended accounts immediately.
    - Emits tamper-evident audit records for both successful and failed attempts.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    user = db.query(User).filter(
        or_(User.username == credentials.username_or_email, User.email == credentials.username_or_email)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        # Audit log failed login
        AuditService.log_event(
            db=db,
            action=AuditAction.USER_LOGIN_FAILED,
            result=AuditResult.DENIED,
            actor_id=user.id if user else None,
            details={"ip": client_ip, "identifier": credentials.username_or_email}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        AuditService.log_event(
            db=db,
            action=AuditAction.USER_LOGIN_FAILED,
            result=AuditResult.DENIED,
            actor_id=user.id,
            details={"ip": client_ip, "reason": "Account is inactive"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator."
        )

    # Audit log successful login
    AuditService.log_event(
        db=db,
        action=AuditAction.USER_LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        actor_id=user.id,
        details={"ip": client_ip, "username": user.username}
    )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs a logout event for accountability."""
    client_ip = request.client.host if request.client else "unknown"
    AuditService.log_event(
        db=db,
        action=AuditAction.USER_LOGOUT,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        details={"ip": client_ip}
    )
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserOut)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Retrieves profile and role information for the currently authenticated user."""
    return current_user
