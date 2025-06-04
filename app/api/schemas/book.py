from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class AddBook(BaseModel):
    title: str
    author: str
    category: str
    summary: str
    
    class Config:
        orm_mode = True

class SearchBook(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    availability: Optional[bool] = None

class FilterBook(BaseModel):
    page: int
    limit: int
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    availability: Optional[bool] = None

class UpdateBook(BaseModel):
    uid:uuid.UUID
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None

class UIDBooks(BaseModel):
    uid:uuid.UUID