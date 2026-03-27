from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SendMessageRequest(BaseModel):
    receiver_username: str
    content: str


class MessageResponse(BaseModel):
    id: int
    sender_username: str
    receiver_username: str
    content: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationRequest(BaseModel):
    receiver_username: str
    title: str
    message: str
    type: Optional[str] = "info"  # info, success, warning, error


class NotificationResponse(BaseModel):
    id: int
    receiver_username: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    message: str