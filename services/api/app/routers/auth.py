"""
Authentication and Account API Routers (SRS Section 5, Module M01).
Provides endpoints for OTP request/verify, onboarding, /me profile, devices, data export and deletion.
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from packages.trust_kernel.auth import AuthException, auth_service, is_dev_mode

router = APIRouter(tags=["Authentication & Account (M01)"])


# --- Schemas ---


class OtpRequestPayload(BaseModel):
    phone: str = Field(
        ..., description="11-digit Bangladesh mobile number", examples=["01711000000"]
    )
    device_id: str | None = None
    device_label: str | None = None
    lang: str = "bn"


class OtpVerifyPayload(BaseModel):
    phone: str = Field(..., examples=["01711000000"])
    code: str = Field(..., examples=["123456"])
    device_id: str | None = None
    device_label: str | None = None


class RefreshPayload(BaseModel):
    refresh_token: str


class OnboardingPayload(BaseModel):
    name: str | None = None
    preferred_lang: str = "bn"
    numeral_style: str = "bn"
    terms_of_service: bool = False
    privacy_policy: bool = False
    ai_disclaimer: bool = False


class UpdateProfilePayload(BaseModel):
    name: str | None = None
    preferred_lang: str | None = None
    numeral_style: str | None = None


class DemoLoginPayload(BaseModel):
    role: str = "citizen"


# --- Auth Dependency ---


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Extract and validate bearer token from Authorization header, cookie, or query param."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
    elif "ain_ai_token" in request.cookies:
        token = request.cookies.get("ain_ai_token")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in via OTP.",
        )

    try:
        user = auth_service.authenticate_token(token)
        return user
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | None:
    """Extract current user if token is present, otherwise return None without raising."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
    elif "ain_ai_token" in request.cookies:
        token = request.cookies.get("ain_ai_token")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if not token:
        return None

    try:
        return auth_service.authenticate_token(token)
    except Exception:
        return None


# --- Routes ---


@router.post("/auth/otp/request", status_code=status.HTTP_200_OK)
def request_otp(payload: OtpRequestPayload, request: Request, response: Response):
    ip = request.client.host if request.client else "127.0.0.1"
    try:
        result = auth_service.request_otp(
            phone=payload.phone,
            ip=ip,
            device_id=payload.device_id,
            device_label=payload.device_label,
            lang=payload.lang,
        )
        if is_dev_mode():
            response.headers["X-Dev-Mode-Warning"] = (
                "Development mode active: OTP code exposed in response"
            )
        return result
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/auth/demo-login", status_code=status.HTTP_200_OK)
def demo_login(payload: DemoLoginPayload, request: Request, response: Response):
    """
    Development-only 1-click login endpoint (Sprint S7 E5).
    Strictly returns 404 when DEV_MODE is false or unset.
    """
    if not is_dev_mode():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo login endpoint disabled in production.",
        )

    import uuid
    from datetime import datetime, timedelta, timezone

    from packages.trust_kernel.auth import TokenService
    from packages.trust_kernel.db import db_manager

    phone = "01700000001" if payload.role == "admin" else "01711223344"
    name = "সিস্টেম অ্যাডমিন" if payload.role == "admin" else "এডভোকেট ডেমো ইউজার"
    role = "admin" if payload.role == "admin" else "citizen"

    now = datetime.now(timezone.utc)
    user_id = auth_service._users_by_phone.get(phone)
    if not user_id:
        user_id = f"demo-{payload.role}-{uuid.uuid4().hex[:6]}"
        user = {
            "id": user_id,
            "phone": phone,
            "name": name,
            "role": role,
            "roles": [role],
            "preferred_lang": "bn",
            "numeral_style": "bn",
            "status": "active",
            "is_onboarded": True,
            "created_at": now.isoformat(),
            "deleted_at": None,
        }
        auth_service._users[user_id] = user
        auth_service._users_by_phone[phone] = user_id
        db_manager.save_user(user)
    else:
        user = auth_service._users[user_id]
        user["role"] = role
        user["roles"] = [role]
        user["is_onboarded"] = True
        db_manager.save_user(user)

    dev_id = f"dev-demo-{uuid.uuid4().hex[:6]}"
    access_payload = {
        "sub": user_id,
        "phone": phone,
        "device_id": dev_id,
        "role": role,
        "roles": [role],
        "type": "access",
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }
    access_token = TokenService.encode_token(access_payload)

    response.set_cookie(
        key="ain_ai_token",
        value=access_token,
        httponly=False,
        samesite="lax",
        path="/",
        max_age=86400,
    )
    response.headers["X-Dev-Mode-Warning"] = "Development mode active: demo-login session issued"
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "role": payload.role,
        "user_id": user_id,
    }


@router.post("/auth/otp/verify", status_code=status.HTTP_200_OK)
def verify_otp(payload: OtpVerifyPayload, request: Request, response: Response):
    ip = request.client.host if request.client else "127.0.0.1"
    try:
        result = auth_service.verify_otp(
            phone=payload.phone,
            code=payload.code,
            device_id=payload.device_id,
            device_label=payload.device_label,
            ip=ip,
        )
        # Set session cookie for seamless browser navigation
        response.set_cookie(
            key="ain_ai_token",
            value=result["access_token"],
            httponly=False,
            samesite="lax",
            path="/",
            max_age=86400,
        )
        return result
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/auth/refresh", status_code=status.HTTP_200_OK)
def refresh_token(payload: RefreshPayload):
    try:
        return auth_service.refresh_tokens(payload.refresh_token)
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
def logout(response: Response, current_user: dict[str, Any] = Depends(get_current_user)):
    auth_service.logout(current_user["id"], current_user.get("device_id"))
    response.delete_cookie("ain_ai_token")
    return {"status": "logged_out", "message": "Session invalidated successfully."}


@router.post("/auth/onboarding", status_code=status.HTTP_200_OK)
def complete_onboarding(
    payload: OnboardingPayload,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        updated_user = auth_service.complete_onboarding(
            user_id=current_user["id"],
            name=payload.name,
            preferred_lang=payload.preferred_lang,
            numeral_style=payload.numeral_style,
            terms_accepted=payload.terms_of_service,
            privacy_accepted=payload.privacy_policy,
            ai_disclaimer_accepted=payload.ai_disclaimer,
        )
        return {"status": "onboarded", "user": updated_user}
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(current_user: dict[str, Any] = Depends(get_current_user)):
    try:
        return auth_service.get_profile(
            current_user["id"], current_device_id=current_user.get("device_id")
        )
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/me", status_code=status.HTTP_200_OK)
def update_me(
    payload: UpdateProfilePayload,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        updated = auth_service.update_profile(
            user_id=current_user["id"],
            name=payload.name,
            preferred_lang=payload.preferred_lang,
            numeral_style=payload.numeral_style,
        )
        return {"status": "updated", "user": updated}
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/me/devices", status_code=status.HTTP_200_OK)
def list_my_devices(current_user: dict[str, Any] = Depends(get_current_user)):
    return {
        "devices": auth_service.list_devices(
            current_user["id"], current_device_id=current_user.get("device_id")
        )
    }


@router.delete("/me/devices/{device_id}", status_code=status.HTTP_200_OK)
def revoke_my_device(
    device_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        auth_service.revoke_device(current_user["id"], device_id)
        return {"status": "revoked", "device_id": device_id}
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/me/export", status_code=status.HTTP_200_OK)
def export_my_data(current_user: dict[str, Any] = Depends(get_current_user)):
    try:
        bundle = auth_service.export_data(current_user["id"])
        return bundle
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/me/delete", status_code=status.HTTP_200_OK)
def delete_my_account(
    response: Response,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        auth_service.delete_account(current_user["id"])
        response.delete_cookie("ain_ai_token")
        return {"status": "deleted", "message": "Account anonymised and deleted successfully."}
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
