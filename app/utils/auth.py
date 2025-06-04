from passlib.context import CryptContext
from jose import jwt,JWTError
from datetime import datetime,timedelta
from fastapi import Header,HTTPException,status
from fastapi.responses import JSONResponse

from startup.db_config import Config


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_data:dict):
    payload = user_data
    payload['exp'] = datetime.utcnow() + timedelta(minutes=60)
    payload['iat'] = datetime.utcnow()
    token = jwt.encode(payload,
                       key=Config.JWT_SECRET,
                       algorithm=Config.JWT_ALGORITHM)
    return token

def decode_token(token:str):
    token_data = jwt.decode(token,
                       key=Config.JWT_SECRET,
                       algorithms=Config.JWT_ALGORITHM)
    return token_data

def get_current_user(authorization: str = Header(None)):
    if not authorization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization header is missing",
            )
    try:
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type. Expected 'Bearer'",
            )
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=Config.JWT_ALGORITHM)
        return payload,''
    except Exception as e:
        return {},str(e)
    
def get_current_admin(authorization: str = Header(None)):
    if not authorization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization header is missing",
            )
    try:
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type. Expected 'Bearer'",
            )
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=Config.JWT_ALGORITHM)
        if payload.get("role") != "admin":
            raise Exception("You do not have permission to access this feature.")
        return payload,''
    except Exception as e:
        return {},str(e)