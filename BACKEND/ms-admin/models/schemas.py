from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    filiere: Optional[str] = None  # optionnel, pour les étudiants

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    filiere: Optional[str] = None  # optionnel

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    filiere: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class AssignRoleRequest(BaseModel):
    username: str
    role: str

class SuccessResponse(BaseModel):
    message: str