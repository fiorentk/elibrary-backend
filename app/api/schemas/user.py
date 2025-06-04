from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class RequestRegisterUser(BaseModel):
    username: str
    password: str
    name: str 
    address: str

class LoginUser(BaseModel):
    username: str
    password: str