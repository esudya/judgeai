"""Password login and revocable browser sessions. No public self-registration."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import delete, select
from starlette.concurrency import run_in_threadpool

from src.api.deps import CurrentUser, DbSession
from src.config import settings
from src.db.auth import User, UserSession
from src.services.auth import (
    SESSION_SECONDS,
    UserContext,
    check_password,
    clear_successful_attempt,
    consume_login_attempt,
    create_session,
    hasher,
    session_payload,
)
from src.services.auth_tokens import token_digest

router = APIRouter()


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: SecretStr


@router.post("/login")
async def login(payload: LoginInput, request: Request, response: Response, db: DbSession):
    if request.headers.get("X-Requested-With") != "JudgeAI":
        raise HTTPException(403, "Login header required")
    client_host = request.client.host if request.client else "unknown"
    if not await consume_login_attempt(db, client_host, payload.username):
        raise HTTPException(429, "Too many login attempts; try again in 15 minutes")
    user = await db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    password = payload.password.get_secret_value()
    valid = await check_password(user.password_hash if user else None, password)
    if not valid or user is None or not user.is_active:
        raise HTTPException(401, "Invalid username or password")
    await clear_successful_attempt(db, client_host, user.username)
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = await run_in_threadpool(hasher.hash, password)
    # Rotating a browser's authenticated session prevents session fixation.
    old_token = request.cookies.get("judgeai_session")
    if old_token:
        await db.execute(
            delete(UserSession).where(UserSession.token_hash == token_digest(old_token))
        )
    token = await create_session(db, user)
    response.set_cookie(
        "judgeai_session",
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return session_payload(UserContext(user.id, user.username, user.is_admin), token)


@router.get("/me")
async def me(request: Request, response: Response, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    return session_payload(user, request.cookies["judgeai_session"])


@router.post("/logout")
async def logout(request: Request, response: Response, db: DbSession, user: CurrentUser):
    await db.execute(
        delete(UserSession).where(
            UserSession.token_hash == token_digest(request.cookies["judgeai_session"])
        )
    )
    await db.commit()
    response.delete_cookie(
        "judgeai_session",
        path="/",
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}
