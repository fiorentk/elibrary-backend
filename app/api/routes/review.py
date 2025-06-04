from fastapi import APIRouter, HTTPException,status,Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel
from typing import List
import uuid
from datetime import datetime,timedelta

from startup.db_config import engine,async_session_factory
from api.schemas.review import AddReview,GetReview,UpdateReview,GetBookReview
from repositories.models import Users, Books,Transactions,BookReviews
from utils.auth import get_current_user


review_router = APIRouter()

@review_router.post("/")
async def add_review(request: AddReview, user_info = Depends(get_current_user)):
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
            
            result = await session.execute(select(Books).where(Books.uid == request.book_id))
            book = result.scalar_one_or_none()
            if not book:
                raise Exception("Book not found.")
            
            result = await session.execute(select(BookReviews).where(BookReviews.user_id == uid,BookReviews.book_id==request.book_id))
            review = result.scalar_one_or_none()
            if review:
                raise Exception("You've already submitted a review for this book.")
            
            new_review = BookReviews(
                user_id=uid,
                book_id=request.book_id,
                rating=request.rating,
                description=request.description
            )

            session.add(new_review)
            await session.commit()
            return {
                'resp_msg': 'Your review has been posted successfully!',
                'resp_data': {
                    'review_id':new_review.uid,
                    'reviewer':username,
                    'book_title':book.title,
                    'rating':new_review.rating,
                    'description':new_review.description
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

@review_router.get("/")
async def get_review(request: GetReview, user_info = Depends(get_current_user)):
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
            result = await session.execute(
                select(BookReviews)
                .options(selectinload(BookReviews.review_user), selectinload(BookReviews.review_book))
                .where(BookReviews.uid == request.review_id)
                )
            review_result = result.scalar_one_or_none()
            if not review_result:
                raise Exception("Review not found.")
            review_user = review_result.review_user
            review_book = review_result.review_book
            return {
                'resp_msg': 'Success.',
                'resp_data': {
                    'review_id':review_result.uid,
                    'reviewer':review_user.username,
                    'book_title':review_book.title,
                    'rating':review_result.rating,
                    'description':review_result.description,
                    'created_at':review_result.created_at
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

@review_router.get("/book")
async def get_book_review(request: GetBookReview, user_info = Depends(get_current_user)):
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
            result = await session.execute(
                select(BookReviews)
                .options(selectinload(BookReviews.review_user), selectinload(BookReviews.review_book))
                .where(BookReviews.book_id == request.book_id)
                )
            review_result = result.scalars().all()
            if not review_result:
                raise Exception("No review found about this book.")
            book_result = review_result[0].review_book
            return {
                'resp_msg': 'Success.',
                'resp_data': {
                    'book_title':book_result.title,
                    "reviews":[{
                        'review_id':review.uid,
                        'reviewer':review.review_user.username,
                        'rating':review.rating,
                        'description':review.description,
                        'created_at':review.created_at,
                        'updated_at':review.updated_at,
                    } for review in review_result]
            }}
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )

@review_router.put("/")
async def update_review(request: UpdateReview, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            uid: str = user_info.get('uid','')
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            result = await session.execute(
                select(BookReviews)
                .options(selectinload(BookReviews.review_book))
                .where(BookReviews.uid == request.review_id,BookReviews.user_id==uid)
                )
            review_result = result.scalar_one_or_none()
            if not review_result:
                raise Exception("Review not found.")
            book_result = review_result.review_book
            if request.rating:
                review_result.rating = request.rating
            if request.description:
                review_result.description = request.description
            session.add(review_result)
            await session.commit()
            await session.refresh(review_result)
            return {
                'resp_msg': 'Review updated.',
                'resp_data': {
                    'review_id':review_result.uid,
                    'reviewer':username,
                    'book_title':book_result.title,
                    'rating':review_result.rating,
                    'description':review_result.description,
                    'created_at':review_result.created_at,
                    'update_at': review_result.updated_at
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

@review_router.delete("/")
async def delete_review(request: GetReview, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            uid: str = user_info.get('uid','')
            
            result = await session.execute(select(Users).where(Users.username == username))
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found.")
            result = await session.execute(
                select(BookReviews)
                .options(selectinload(BookReviews.review_book))
                .where(BookReviews.uid == request.review_id,BookReviews.user_id==uid)
                )
            review_result = result.scalar_one_or_none()
            if not review_result:
                raise Exception("Review not found.")
            
            await session.delete(review_result)
            await session.commit()
            return {
                'resp_msg': 'Review deleted.',
                'resp_data': None
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': None
            }
        )