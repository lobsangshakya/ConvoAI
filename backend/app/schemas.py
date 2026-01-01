from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatLogBase(BaseModel):
    user_id: str
    session_id: str
    user_message: str
    bot_response: str
    reward_score: Optional[float] = 0.0


class ChatLogCreate(ChatLogBase):
    pass


class ChatLog(ChatLogBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    user_id: str
    username: str
    email: str


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True