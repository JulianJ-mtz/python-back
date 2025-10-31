from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    mail: EmailStr


class UserResponse(BaseModel):
    id: int
    name: str
    mail: str

    class Config:
        from_attributes: bool = True


class UserRegister(UserCreate):
    name: str
    mail: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
