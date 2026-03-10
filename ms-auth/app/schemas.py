from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    roles: list[str]
