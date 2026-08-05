"""Modelos Pydantic para autenticación."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credenciales requeridas por el endpoint de inicio de sesión."""

    email: EmailStr
    password: str = Field(..., min_length=6)
