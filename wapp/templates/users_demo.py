# users_demo.py — simple Users demo Wapp: DB URLs, model, Wapp and auth endpoints
# This template is copied into the user's project by wapp-init and mirrors the repo demo layout.

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr
from sqlalchemy import select, String, Integer, Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from wapp.core.asgi import Wapp, WappEndpoint, EndpointMeta, BaseModel as DeclarativeBaseModel

# --- Model: single User model in the demo (inherits wapp.core.asgi.BaseModel)
class User(DeclarativeBaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    class Meta:
        slug = "users"

# --- Request/response models for auth endpoints ---
class CheckEmailReq(BaseModel):
    email: EmailStr

class CheckEmailRes(BaseModel):
    exists: bool

class SignupReq(BaseModel):
    email: EmailStr

class SignupRes(BaseModel):
    id: int
    email: EmailStr

# --- Custom endpoints as WappEndpoint subclasses ---
class CheckEmailEndpoint(WappEndpoint):
    Meta = EndpointMeta(
        method="POST",
        pattern="/auth/check_email",
        name="check_email",
        request_model=CheckEmailReq,
        response_model=CheckEmailRes,
    )

    async def handle(self, request, query: Dict[str, Any], path: Dict[str, Any], body: Any, session: AsyncSession):
        email = getattr(body, "email", None) if body is not None else None
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        user = res.scalars().first()
        return CheckEmailRes(exists=bool(user))

class SignupEndpoint(WappEndpoint):
    Meta = EndpointMeta(
        method="POST",
        pattern="/auth/signup",
        name="signup",
        request_model=SignupReq,
        response_model=SignupRes,
    )

    async def handle(self, request, query: Dict[str, Any], path: Dict[str, Any], body: Any, session: AsyncSession):
        email = getattr(body, "email", None) if body is not None else None
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        if res.scalars().first():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        from pydantic import EmailStr as _EmailStr
        return SignupRes(id=user.id, email=_EmailStr(user.email))

# --- Wapp definition ---
class UsersWapp(Wapp):
    class Models:
        user = User

    class Endpoints:
        # Auto-generate CRUD for the `user` model
        _user = True
        check_email = CheckEmailEndpoint
        signup = SignupEndpoint

    class Wapps:
        ...


__all__ = ["UsersWapp"]
