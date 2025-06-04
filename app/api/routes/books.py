from fastapi import APIRouter, HTTPException,status,Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_,func,asc,desc
from sqlmodel import SQLModel
from typing import List
import uuid
from sqlalchemy.exc import IntegrityError

from startup.db_config import engine,async_session_factory
from api.schemas.book import AddBook,SearchBook,UpdateBook,UIDBooks,FilterBook
from repositories.models import Users, Books
from utils.auth import get_current_user


book_router = APIRouter()

@book_router.post("/")
async def add_book(request: AddBook, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            uid: str = user_info.get('uid','')
            username: str = user_info.get('username','')
            role: str = user_info.get('role','')
            
            if role != 'admin':
                raise Exception("You do not have permission to access this feature.")
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            new_book = Books(
                title=request.title,
                author=request.author,
                category=request.category,
                summary=request.summary,
                admin_id=uid
            )

            session.add(new_book)
            await session.commit()
            session.refresh(new_book)
            return {
                'resp_msg': 'The book has been successfully added to the e-library',
                'resp_data': {
                    'title':new_book.title,
                    'author':new_book.author,
                    'category':new_book.category,
                    'summary':new_book.summary,
                    'availability':new_book.availability
                }
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@book_router.post("/multiple/")
async def add_multiple_book(request: list[AddBook], user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            uid: str = user_info.get('uid','')
            username: str = user_info.get('username','')
            role: str = user_info.get('role','')
            
            if role != 'admin':
                raise Exception("You do not have permission to access this feature.")
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            empty_fields = set()
            for book_request in request:
                if not book_request.title.strip():
                    empty_fields.add("Title")
                if not book_request.author.strip():
                    empty_fields.add("Author")
                if not book_request.category.strip():
                    empty_fields.add("Category")
                if not book_request.summary.strip():
                    empty_fields.add("Summary")
            if empty_fields:
                raise Exception(f"{', '.join(empty_fields)} field(s) cannot be empty.")

            new_books=[]
            for book_request  in request:
                new_book = Books(
                    title=book_request.title,
                    author=book_request.author,
                    category=book_request.category,
                    summary=book_request.summary,
                    admin_id=uid
                )
                new_books.append(new_book)
                session.add(new_book)


            await session.commit()
            session.refresh(new_book)
            return {
                'resp_msg': 'The book has been successfully added to the e-library',
                'resp_data': [{
                    'title':book.title,
                    'author':book.author,
                    'category':book.category
                } for book in new_books]
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

from sqlalchemy import func

@book_router.post("/filter")
async def search_book_filter(request: FilterBook):
    async with async_session_factory() as session:
        try:
            offset = (request.page - 1) * request.limit

            # Base query with filters
            base_query = select(Books)
            if request.title:
                base_query = base_query.where(Books.title.ilike(f'%{request.title}%'))
            if request.author:
                base_query = base_query.where(Books.author.ilike(f'%{request.author}%'))
            if request.category:
                base_query = base_query.where(Books.category.ilike(f'%{request.category}%'))
            if request.availability is not None:
                base_query = base_query.where(Books.availability == request.availability)

            # Total count query
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Books.title))
            )
            books_result = result.scalars().all()

            if not books_result:
                raise Exception("No books found matching the given criteria.")

            return {
                'resp_msg': 'Books based on filter.',
                'resp_data': [{
                    'title': book.title,
                    'author': book.author,
                    'category': book.category,
                    'summary': book.summary,
                    'availability': book.availability
                } for book in books_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }

        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'resp_msg': str(e),
                    'resp_data': None
                }
            )

@book_router.post("/by-uid")
async def search_book_filter(request: list[UIDBooks], user_info=Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info = user_info[0]
            username: str = user_info.get('username', '')
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            # ✅ Extract UID list
            uid_list = [book.uid for book in request]

            result = await session.execute(select(Books).where(Books.uid.in_(uid_list)))
            books_result = result.scalars().all()
            if not books_result:
                raise Exception("No books found matching the given uid.")
            
            return {
                'resp_msg': 'Books based on filter.',
                'resp_data': [
                    {   'uid':book.uid,
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'summary': book.summary,
                        'availability': book.availability
                    } for book in books_result
                ]
            }
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'resp_msg': str(e),
                    'resp_data': None
                }
            )


@book_router.get("/available")
async def available_book():
    async with async_session_factory() as session:
        try:
            result = await session.execute(select(Books).order_by(func.random()).where(Books.availability == True).limit(10))
            books_result = result.scalars().all()
            if not books_result:
                raise Exception("No books available.")
            return {
                'resp_msg': 'Here is the list of available books.',
                'resp_data': [{
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'summary': book.summary,
                        'availability': book.availability
                    } for book in books_result
                ]
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@book_router.put("/")
async def update_book(request: UpdateBook, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            uid: str = user_info.get('uid','')
            username: str = user_info.get('username','')
            role: str = user_info.get('role','')
            
            if role != 'admin':
                raise Exception("You do not have permission to access this feature.")
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            result = await session.execute(select(Books).where(Books.uid == request.uid))
            book_result = result.scalar_one_or_none()
            if not book_result:
                raise Exception("Book not found.")
            
            empty_fields = set()
            if not request.title.strip():
                empty_fields.add("Title")
            if not request.author.strip():
                empty_fields.add("Author")
            if not request.category.strip():
                empty_fields.add("Category")
            if not request.summary.strip():
                empty_fields.add("Summary")
            if empty_fields:
                raise Exception(f"{', '.join(empty_fields)} field(s) cannot be empty.")

            if request.title:
                book_result.title = request.title
            if request.author:
                book_result.author = request.author
            if request.category:
                book_result.category = request.category
            if request.summary:
                book_result.summary = request.summary
        
            session.add(book_result)
            await session.commit()
            await session.refresh(book_result)
            return {
                'resp_msg': "The book's detail has been updated successfully.",
                'resp_data': {
                    'title':book_result.title,
                    'author':book_result.author,
                    'category':book_result.category,
                    'summary':book_result.summary
                }
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@book_router.delete("/{book_id}")
async def delete_book(book_id: uuid.UUID, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            uid: str = user_info.get('uid','')
            username: str = user_info.get('username','')
            role: str = user_info.get('role','')
            
            if role != 'admin':
                raise Exception("You do not have permission to access this feature.")
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            result = await session.execute(select(Books).where(Books.uid == book_id))
            book_result = result.scalar_one_or_none()
            if not book_result:
                raise Exception("Book not found.")
            
            await session.delete(book_result)
            await session.commit()
            return {
                'resp_msg': 'The book has been deleted.',
                'resp_data': None
            }
        except IntegrityError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'resp_msg': "The book is being requested or borrowed; you can't delete it.",
                    'resp_data': None
                }
            )
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@book_router.post("/by-title")
async def book_by_title(request: SearchBook, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            
            query = select(Books)
            if request.title:
                query = query.where(Books.title.ilike(f'%{request.title}%'))

            result = await session.execute(query.order_by(asc(Books.title)).limit(10))
            books_result = result.scalars().all()
            if not books_result:
                raise Exception("No books found.")
            
            return {
                'resp_msg': 'Books based on filter.',
                'resp_data': [{
                        'uid':book.uid,
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'summary': book.summary,
                        'availability': book.availability
                    } for book in books_result
                ]
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )
