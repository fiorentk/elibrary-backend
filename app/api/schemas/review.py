from pydantic import BaseModel, Field, confloat
from typing import List, Optional
from datetime import datetime
import uuid

class AddReview(BaseModel):
    book_id: uuid.UUID
    rating: confloat(gt=0, le=5, multiple_of=0.1,)
    description: Optional[str] = None

    class Config:
        orm_mode = True

class GetReview(BaseModel):
    review_id: uuid.UUID

class GetBookReview(BaseModel):
    book_id: uuid.UUID

class UpdateReview(BaseModel):
    review_id: uuid.UUID
    rating:  Optional[confloat(gt=0, le=5, multiple_of=0.1,)]
    description: Optional[str] = None