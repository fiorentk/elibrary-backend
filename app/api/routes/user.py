from fastapi import APIRouter, HTTPException,status, Header,Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_,func,asc,desc
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel
from typing import List
import uuid
from jose import jwt, JWTError, ExpiredSignatureError

from startup.db_config import engine,async_session_factory,Config
from api.schemas.user import RequestRegisterUser,LoginUser
from repositories.models import Users, Books,Transactions, Requests
from utils.auth import get_password_hash,verify_password,create_access_token,decode_token,get_current_user


user_router = APIRouter()

@user_router.post("/register-user/")
async def register_user(request: RequestRegisterUser):
    async with engine.begin() as conn:
        try:
            empty_fields = []
            if not request.username.strip():
                empty_fields.append("Username")
            if not request.password.strip():
                empty_fields.append("Password")
            if not request.name.strip():
                empty_fields.append("Name")
            if not request.address.strip():
                empty_fields.append("Address")
            if empty_fields:
                raise Exception(f"{', '.join(empty_fields)} field cannot be empty.")

            result = await conn.execute(
                text("SELECT username FROM users WHERE username = :username"),
                {"username": request.username})
            existing_user = result.mappings().first()
            if existing_user:
                raise Exception("The username is already in use.") 
            result = await conn.execute(
                text("""INSERT INTO users (uid, username, password, name, address, created_at) 
                    VALUES (:uid, :username, :password, :name, :address, NOW())
                    RETURNING username, name, address"""),
                {"username": request.username,
                  "name":request.name.upper(),
                  "uid": uuid.uuid4(),
                  "address": request.address.upper(),
                  "password":get_password_hash(request.password)}
            )
            new_user = result.mappings().first()
            await conn.commit()
            return {
                'resp_msg': 'User created successfully',
                'resp_data': new_user
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@user_router.post("/login/")
async def login(request: LoginUser):
    async with engine.begin() as conn:
        try: 
            empty_fields = []
            if not request.username.strip():
                empty_fields.append("Username")
            if not request.password.strip():
                empty_fields.append("Password")
            if empty_fields:
                raise Exception(f"{', '.join(empty_fields)} field cannot be empty.")
                
            result = await conn.execute(
                text("SELECT uid, username, password,role FROM users WHERE username = :username"),
                {"username": request.username})
            existing_user = result.mappings().first()
            if not existing_user:
                raise Exception("Username atau password salah.") 
            is_correct_password = verify_password(request.password,existing_user.password)
            if not is_correct_password:
                raise Exception("Username atau password salah.")
            existing_user_json = {
                "uid": str(existing_user.uid),
                "username": existing_user.username,
                "role":existing_user.role
                }
            token = create_access_token(existing_user_json)
            return {
                'resp_msg': "Login success.",
                'resp_data':{
                    "access_token": token,
                    "token_type": "bearer"}}
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@user_router.get("/info/")
async def info(user_info = Depends(get_current_user)):
    async with engine.begin() as conn:
        try:    
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            result = await conn.execute(
                text("SELECT username, name, role, address,created_at FROM users WHERE username = :username"),
                {"username": username}
            )
            user = result.mappings().first() 
            if not user:
                raise Exception("User not found")
            return {
                'resp_msg': 'Success',
                'resp_data': {
                        'username': user.username,
                        'name': user.name,
                        'address': user.address,
                        'role': user.role,
                        'created_at': user.created_at.date().isoformat()
                    }
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@user_router.get("/summary/")
async def info(user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            uid: str = user_info.get('uid','')
            username: str = user_info.get('username','')

            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            base_query =(select(Requests.book_id)
                         .where(Requests.user_id == uid,Requests.status != 'pending'))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_books_borrowed = await session.execute(count_query)
            total_books_borrowed = total_books_borrowed.scalar()   
            
            base_query =(select(Requests)
                         .where(Requests.user_id == uid,Requests.status == 'pending'))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_pending_req = await session.execute(count_query)
            total_pending_req = total_pending_req.scalar()   
            
            base_query =(select(Requests)
                         .where(Requests.user_id == uid,Requests.status == 'accepted'))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_accepted_req = await session.execute(count_query)
            total_accepted_req = total_accepted_req.scalar()   
            
            base_query =(select(Requests)
                         .where(Requests.user_id == uid,Requests.status == 'rejected'))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_rejected_req = await session.execute(count_query)
            total_rejected_req = total_rejected_req.scalar()   
            
            base_query =(select(Transactions)
                            .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                            .where(Transactions.returned_at.is_(None),
                                    Requests.request_user.has(uid=user.uid)))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_ongoing_trx = await session.execute(count_query)
            total_ongoing_trx = total_ongoing_trx.scalar()   
                        
            base_query =(select(Transactions)
                            .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                            .where(Transactions.returned_at.is_not(None),
                                    Requests.request_user.has(uid=user.uid)))
            count_query = select(func.count()).select_from(base_query.subquery())
            total_finished_trx = await session.execute(count_query)
            total_finished_trx = total_finished_trx.scalar()   
            
            return {
                'resp_msg': 'Success',
                'resp_data': {
                        'username': user.username,
                        'total_books_borrowed': total_books_borrowed,
                        'total_pending_req': total_pending_req,
                        'total_accepted_req': total_accepted_req,
                        'total_rejected_req': total_rejected_req,
                        'total_ongoing_trx': total_ongoing_trx,
                        'total_finished_trx': total_finished_trx
                    }
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@user_router.get("/check-token/")
async def check_token(authorization: str = Header(None)):
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
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return {
            'resp_msg': 'Valid',
            'resp_data': {"is_valid":True}
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'resp_msg': str(e),
                'resp_data': {"is_valid":False}
            }
        )
    
@user_router.get("/check-admin/")
async def check_admin(user_info = Depends(get_current_user)):
    async with engine.begin() as conn:
        try:    
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            result = await conn.execute(
                text("SELECT role:role FROM users WHERE username = :username"),
                {"role":"admin","username": username}
            )
            user = result.mappings().first() 
            if not user:
                raise Exception("The user is not an administrator.")
            return {
                'resp_msg': 'Valid',
                'resp_data': {"is_admin": True} 
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content = {
                'resp_msg': str(e),
                'resp_data': {"is_admin":False}
            }
        )