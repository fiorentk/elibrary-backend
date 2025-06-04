from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class RequestBorrow(BaseModel):
    book_id: uuid.UUID
    duration: int
    
    class Config:
        orm_mode = True

class PendingRequest(BaseModel):
    request_id : uuid.UUID
    description: Optional[str] = None

    class Config:
        orm_mode = True

class ReturnBook(BaseModel):
    transaction_id: uuid.UUID
    
    class Config:
        orm_mode = True

class Pagination(BaseModel):
    page: int
    limit: int