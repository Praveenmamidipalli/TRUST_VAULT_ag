from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.rate_limiter import auth_rate_limiter
from app.core.otp_service import otp_service
from app.models.user import User
from app.models.enums import UserRole, AuditAction, AuditResult
from app.schemas.user import UserCreate, UserLogin, UserOut, TokenResponse
from app.middleware.auth_deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Request2FAResponse(BaseModel):
    status: str
    user_id: int
    email: str
    demo_otp: str
    expires_in_seconds: int
    message: str


class Verify2FARequest(BaseModel):
    user_id: int
    otp_code: str = Field(..., min_length=6, max_length=6)


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
    existing_user = db.query(User).filter(
        or_(User.email == user_in.email, User.username == user_in.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email or username already exists."
        )

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
    """Authenticates a user via username/email and password. Returns signed JWT."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{credentials.username_or_email.lower().strip()}"

    is_limited, retry_after = auth_rate_limiter.is_rate_limited(rate_key)
    if is_limited:
        AuditService.log_event(
            db=db,
            action=AuditAction.USER_LOGIN_FAILED,
            result=AuditResult.DENIED,
            details={"ip": client_ip, "reason": "Rate limit exceeded (brute-force defense)", "retry_after": retry_after}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Rate limit exceeded. Please wait {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    user = db.query(User).filter(
        or_(User.username == credentials.username_or_email, User.email == credentials.username_or_email)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        auth_rate_limiter.record_failure(rate_key)
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

    auth_rate_limiter.reset(rate_key)

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


@router.post("/request-2fa", response_model=Request2FAResponse)
def request_2fa_challenge(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Initiates Two-Factor Authentication. Verifies primary password, generates a 6-digit OTP,
    and returns simulated dispatch payload with demo OTP for instant evaluation.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{credentials.username_or_email.lower().strip()}"

    is_limited, retry_after = auth_rate_limiter.is_rate_limited(rate_key)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {retry_after} seconds."
        )

    user = db.query(User).filter(
        or_(User.username == credentials.username_or_email, User.email == credentials.username_or_email)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        auth_rate_limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated."
        )

    auth_rate_limiter.reset(rate_key)
    otp_code = otp_service.generate_otp(user.id)

    return Request2FAResponse(
        status="2fa_required",
        user_id=user.id,
        email=user.email,
        demo_otp=otp_code,
        expires_in_seconds=300,
        message=f"Security OTP code dispatched to {user.email}. (Demo Code: {otp_code})"
    )


@router.post("/verify-2fa", response_model=TokenResponse)
def verify_2fa_challenge(
    payload: Verify2FARequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verifies a 6-digit OTP and issues the final JWT bearer access token."""
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    is_valid, err_msg = otp_service.verify_otp(payload.user_id, payload.otp_code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    client_ip = request.client.host if request.client else "unknown"
    AuditService.log_event(
        db=db,
        action=AuditAction.USER_LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        actor_id=user.id,
        details={"ip": client_ip, "2fa_verified": True, "auth_method": "password_plus_otp"}
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
