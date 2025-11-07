import uuid

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr

    class Config:
        from_attributes: bool = True


class UserRegister(UserCreate):
    pass


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ScoreCreate(BaseModel):
    mode: str
    mode_value: int
    total_clicks: int
    correct_clicks: int
    duration: float
    consistency: float | None = None


class ScoreResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    mode_value: int
    cps: float
    total_clicks: int
    correct_clicks: int
    duration: float
    accuracy: float
    consistency: float | None
    created_at: str

    class Config:
        from_attributes: bool = True
        arbitrary_types_allowed: bool = True


class LeaderboardEntry(BaseModel):
    score: ScoreResponse
    user_email: str

    class Config:
        from_attributes: bool = True


class PersonalBests(BaseModel):
    time: dict[str, ScoreResponse | None]
    clicks: dict[str, ScoreResponse | None]


class AverageStats(BaseModel):
    avg_cps: float
    avg_accuracy: float
    avg_consistency: float
    total_tests: int


class JWTPayload(BaseModel):
    sub: str
    type: str
    exp: int
    iat: int
