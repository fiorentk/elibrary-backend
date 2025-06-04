from fastapi import APIRouter, HTTPException,status,Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_,func,asc,desc
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel
from typing import List
import uuid
from datetime import datetime,timedelta

from startup.db_config import engine,async_session_factory
from api.schemas.transaction import RequestBorrow,ReturnBook,PendingRequest,Pagination
from repositories.models import Users, Books,Transactions, Requests
from utils.auth import get_current_user,get_current_admin

transaction_router = APIRouter()

@transaction_router.post("/borrow-request/")
async def borrow_request(request: RequestBorrow, user_info = Depends(get_current_user)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            uid: str = user_info.get('uid','')
            
            result = await session.execute(select(Users).where(Users.username == username))
            user_borrow = result.scalar_one_or_none()
            if not user_borrow:
                raise Exception("User not found.")
            result = await session.execute(select(Books).where(Books.uid == request.book_id))
            book_result = result.scalar_one_or_none()
            if not book_result:
                raise Exception("Book not found.")
            if book_result.availability == False:
                raise Exception("Book is not available.")
            
            result = await session.execute(select(Requests).where((Requests.book_id == request.book_id) & (Requests.user_id == uid) & (Requests.status =='pending')))
            req_result = result.scalar_one_or_none()
            if req_result:
                raise Exception("You're already requesting for this book, please wait for your request to be processed.")

            new_request = Requests(
                user_id=user_borrow.uid,
                book_id=book_result.uid,
                requested_at=datetime.utcnow(),
                duration=request.duration
            )
                        
            session.add(new_request)
            await session.commit()
            return {
                'resp_msg': 'Request is sent!',
                'resp_data': {
                    'borrower':user_borrow.username,
                    'borrowed_book':book_result.title,
                    'duration':new_request.duration
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

@transaction_router.post("/pending-request/")
async def pending_request(request: Pagination, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            
            result_admin = await session.execute(select(Users).where(Users.username == username))
            user_admin = result_admin.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            

            offset = (request.page - 1) * request.limit
            base_query = (select(Requests)
                          .options(selectinload(Requests.borrowed_book),selectinload(Requests.request_user))
                          .where(Requests.status == "pending"))

            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Requests.requested_at)))
            request_result = result.scalars().all()

            if not request_result:
                raise Exception("There is no request that requires processing.")

            return {
                'resp_msg': 'Pending request:',
                'resp_data': [{
                    'uid':request.uid,
                    'username':request.request_user.username,
                    'name':request.request_user.name,
                    'book_title':request.borrowed_book.title,
                    'date_request': request.requested_at.date().isoformat(),
                    'time_request': request.requested_at.time().isoformat(timespec='minutes'),
                    'duration':request.duration,
                    'status':request.status
                } for request in request_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/processed-request/")
async def processed_request(request: Pagination, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            
            result_admin = await session.execute(select(Users).where(Users.username == username))
            user_admin = result_admin.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            base_query = (select(Requests)
                          .options(selectinload(Requests.borrowed_book),selectinload(Requests.request_user))
                          .where(Requests.status.in_(["accepted","rejected"])))

            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Requests.requested_at)))
            request_result = result.scalars().all()

            if not request_result:
                raise Exception("No processed request is found.")

            return {
                'resp_msg': 'Processed request:',
                'resp_data': [{
                    'uid':request.uid,
                    'username':request.request_user.username,
                    'name':request.request_user.name,
                    'book_title':request.borrowed_book.title,
                    'date_request': request.requested_at.date().isoformat(),
                    'time_request': request.requested_at.time().isoformat(timespec='minutes'),
                    'date_update': request.updated_at.date().isoformat(),
                    'time_update': request.updated_at.time().isoformat(timespec='minutes'),
                    'duration':request.duration,
                    'description':request.description,
                    'status':request.status
                } for request in request_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/accept/")
async def accept(request: PendingRequest, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')

            result = await session.execute(select(Users).where(Users.username == username))
            user_admin = result.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            result = await session.execute(select(Requests)
                                           .options(selectinload(Requests.borrowed_book))
                                           .where(Requests.uid == request.request_id))
            request_result = result.scalar_one_or_none()
            if not request_result:
                raise Exception("No request found.")
            if request_result.status != "pending":
                raise Exception("This request has already been processed.")

            book_result = request_result.borrowed_book
            if not book_result:
                raise Exception("Book not found.")
            if book_result.availability == False:
                raise Exception("Book is not available.")
            book_result.availability = False

            result = await session.execute(
                select(Requests)
                .options(selectinload(Requests.borrowed_book))
                .where(
                    Requests.book_id == book_result.uid,
                    Requests.uid != request.request_id,
                    Requests.status == "pending"
                )
            )
            rejected_requests = result.scalars().all()
            for req in rejected_requests:
                req.status = "rejected"
                req.description = "This request is automatically rejected because the book has already been borrowed"
            
            due_date = datetime.utcnow() + timedelta(days=request_result.duration)
            due_date = due_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            new_transaction = Transactions(
                admin_id=user_admin.uid,
                request_id=request_result.uid,
                due_date=due_date
            )

            request_result.status = "accepted"
            request_result.updated_at = datetime.utcnow()
            if request.description:
                request_result.description = request.description
            session.add(new_transaction)
            
            await session.commit()
            return {
                    'resp_msg': 'Request accepted!',
                    'resp_data': {'New transaction':{
                        'request_id':new_transaction.request_id,
                        'created_at': new_transaction.created_at,
                        'due_date': new_transaction.due_date
                    },'Rejected Requests':
                    [
                    {   'uid':req.uid,
                        'user_id': req.user_id,
                        'book_id': req.book_id,
                        'status': req.status,
                        'description': req.description,
                        'date_update': req.updated_at.date().isoformat(),
                        'time_update': req.updated_at.time().isoformat(timespec='minutes'),
                    } for req in rejected_requests
                ]
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

@transaction_router.post("/reject/")
async def reject(request: PendingRequest, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            result = await session.execute(select(Users).where(Users.username == username))
            user_admin = result.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            result = await session.execute(select(Requests).where(Requests.uid == request.request_id))
            request_result = result.scalar_one_or_none()
            if not request_result:
                raise Exception("No request found.")
            if request_result.status != "pending":
                raise Exception("This request has already been processed.")

            request_result.status = "rejected"
            request_result.updated_at = datetime.utcnow()
            if request.description:
                request_result.description = request.description
            session.add(request_result)
            await session.commit()
            return {
                    'resp_msg': 'Request rejected!',
                    'resp_data': {
                        'request_id':request_result.uid,
                        'status': request_result.status,
                        'description': request_result.description,
                        'date_update': request_result.updated_at.date().isoformat(),      # 'YYYY-MM-DD'
                        'time_update': request_result.updated_at.time().isoformat(timespec='minutes'),  # 'HH:MM'

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

@transaction_router.post("/ongoing-transaction/")
async def ongoing_transaction(request : Pagination, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            
            result_admin = await session.execute(select(Users).where(Users.username == username))
            user_admin = result_admin.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            base_query = (select(Transactions)
                          .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.borrowed_book),
                                   selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                          .where(Transactions.returned_at.is_(None)))
            
            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Transactions.due_date)))
            transaction_result = result.scalars().all()

            if not transaction_result:
                raise Exception("There is no ongoing transactions.")

            return {
                'resp_msg': 'Ongoing transactions:',
                'resp_data': [{
                    'uid':trx.uid,
                    'name':trx.transaction_from_request.request_user.name,
                    'book_title':trx.transaction_from_request.borrowed_book.title,
                    'date_create': trx.created_at.date().isoformat(),      # 'YYYY-MM-DD'
                    'time_create': trx.created_at.time().isoformat(timespec='minutes'),  # 'HH:MM'
                    'due_date': trx.due_date.date().isoformat()
                } for trx in transaction_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/finished-transaction/")
async def finished_transaction(request : Pagination, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            
            result_admin = await session.execute(select(Users).where(Users.username == username))
            user_admin = result_admin.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            base_query = (select(Transactions)
                            .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.borrowed_book),
                                    selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                            .where(Transactions.returned_at.is_not(None)))
            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Transactions.due_date)))
            transaction_result = result.scalars().all()
            if not transaction_result:
                raise Exception("There is no finished transactions.")

            return {
                'resp_msg': 'Finished transactions:',
                'resp_data': [{
                    'uid':trx.uid,
                    'name':trx.transaction_from_request.request_user.name,
                    'book_title':trx.transaction_from_request.borrowed_book.title,
                    'date_returned': trx.returned_at.date().isoformat(),
                    'time_returned': trx.returned_at.time().isoformat(timespec='minutes'),
                    'due_date': trx.due_date.date().isoformat(),
                    'is_overdue': trx.is_overdue
                } for trx in transaction_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )
@transaction_router.post("/user-ongoing-transaction/")
async def user_ongoing_transaction(request : Pagination, user_info = Depends(get_current_user)):
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
            
            base_query = (select(Transactions)
                            .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.borrowed_book),
                                    selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                            .where(Transactions.returned_at.is_(None),
                                    Requests.request_user.has(uid=user.uid)))
            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit) .order_by(asc(Transactions.due_date)))
            transaction_result = result.scalars().all()
            if not transaction_result:
                raise Exception("You have no ongoing transaction.")

            return {
                'resp_msg': 'Ongoing transactions:',
                'resp_data': [{
                    'uid':trx.uid,
                    'name':trx.transaction_from_request.request_user.name,
                    'book_title':trx.transaction_from_request.borrowed_book.title,
                    'date_create': trx.created_at.date().isoformat(),
                    'time_create': trx.created_at.time().isoformat(timespec='minutes'),
                    'due_date': trx.due_date.date().isoformat()
                } for trx in transaction_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/user-finished-transaction/")
async def user_finished_transaction(request : Pagination,user_info = Depends(get_current_user)):
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
            
            base_query =(select(Transactions)
                            .options(selectinload(Transactions.transaction_from_request).selectinload(Requests.borrowed_book),
                                    selectinload(Transactions.transaction_from_request).selectinload(Requests.request_user))
                            .where(Transactions.returned_at.is_not(None),
                                    Requests.request_user.has(uid=user.uid)))
            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit) .order_by(asc(Transactions.due_date)))
            transaction_result = result.scalars().all()
            if not transaction_result:
                raise Exception("You have no finished transaction.")

            return {
                'resp_msg': 'Finished transactions:',
                'resp_data': [{
                    'uid':trx.uid,
                    'name':trx.transaction_from_request.request_user.name,
                    'book_title':trx.transaction_from_request.borrowed_book.title,
                    'date_returned': trx.returned_at.date().isoformat(),
                    'time_returned': trx.returned_at.time().isoformat(timespec='minutes'),
                    'due_date': trx.due_date.date().isoformat(),
                    'is_overdue': trx.is_overdue
                } for trx in transaction_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/return/")
async def return_book(request: ReturnBook, user_info = Depends(get_current_admin)):
    async with async_session_factory() as session:
        try:
            if user_info[1] != '':
                raise Exception(user_info[1])
            user_info=user_info[0]
            username: str = user_info.get('username','')
            result = await session.execute(select(Users).where(Users.username == username))
            user_admin = result.scalar_one_or_none()
            if not user_admin:
                raise Exception("User not found.")
            
            result = await session.execute(
                select(Transactions)
                .options(
                    selectinload(Transactions.transaction_from_request)
                    .selectinload(Requests.borrowed_book)
                )
                .options(
                    selectinload(Transactions.transaction_from_request)
                    .selectinload(Requests.request_user)
                )
                .where(Transactions.uid == request.transaction_id))

            transaction_result = result.scalar_one_or_none()
            if not transaction_result:
                raise Exception("No transaction found.")
            if transaction_result.returned_at:
                raise Exception("The transaction is complete; the book has already been returned.")
            
            request_data = transaction_result.transaction_from_request
            request_user = transaction_result.transaction_from_request.request_user
            if request_data.status == "pending" or request_data.status == "rejected":
                raise Exception("This request is still pending or has already been rejected.")
            borrowed_book = transaction_result.transaction_from_request.borrowed_book
            if not borrowed_book:
                raise Exception("Book information is missing from the transaction.")
            
            borrowed_book.availability = True
            transaction_result.returned_at = datetime.utcnow()

            if transaction_result.returned_at > transaction_result.due_date:
                transaction_result.is_overdue = True
                response_msg = 'This book has been successfully returned.The related book is overdue. Please make sure to return books on time in the future.'
            else:
                transaction_result.is_overdue = False
                response_msg = 'This book has been successfully returned. Thank you for returning the related book on time. We appreciate your timely return!'
            
            session.add(transaction_result)
            await session.commit()
            return {
                'resp_msg': response_msg,
                'resp_data': {
                    'borrower_name':request_user.name,
                    'book_title':borrowed_book.title,
                    'date_create': transaction_result.created_at.date().isoformat(),
                    'time_create': transaction_result.created_at.time().isoformat(timespec='minutes'),
                    'date_returned':transaction_result.returned_at.date().isoformat(),
                    'time_returned': transaction_result.returned_at.time().isoformat(timespec='minutes'),
                    'due_date':transaction_result.due_date.date().isoformat(),
                    'is_overdue':transaction_result.is_overdue
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

@transaction_router.post("/user-pending-request/")
async def user_pending_request(request : Pagination, user_info = Depends(get_current_user)):
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
            
            offset = (request.page - 1) * request.limit
            base_query = select(Requests).options(selectinload(Requests.borrowed_book),selectinload(Requests.request_user)).where(Requests.status == "pending",Requests.request_user.has(uid=user.uid))
            count_query = select(func.count()).select_from(base_query)
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Requests.requested_at)))
            request_result = result.scalars().all()
            if not request_result:
                raise Exception("You have no pending request.")

            return {
                'resp_msg': 'Pending request:',
                'resp_data': [{
                    'uid':request.uid,
                    'username':request.request_user.username,
                    'name':request.request_user.name,
                    'book_title':request.borrowed_book.title,
                    'date_request': request.requested_at.date().isoformat(),
                    'time_request': request.requested_at.time().isoformat(timespec='minutes'),
                    'duration':request.duration,
                    'status':request.status
                } for request in request_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

@transaction_router.post("/user-processed-request/")
async def user_processed_request(request : Pagination, user_info = Depends(get_current_user)):
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
            
            base_query = (select(Requests)
                            .options(selectinload(Requests.borrowed_book),selectinload(Requests.request_user))
                            .where(Requests.status.in_(["accepted","rejected"]),
                                    Requests.request_user.has(uid=user.uid)))
            offset = (request.page - 1) * request.limit
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Paginated data
            result = await session.execute(
                base_query.offset(offset).limit(request.limit).order_by(asc(Requests.requested_at)))
            request_result = result.scalars().all()
            if not request_result:
                raise Exception("You have no processed request.")

            return {
                'resp_msg': 'Processed request:',
                'resp_data': [{
                    'uid':request.uid,
                    'username':request.request_user.username,
                    'name':request.request_user.name,
                    'book_title':request.borrowed_book.title,
                    'date_request': request.requested_at.date().isoformat(),
                    'time_request': request.requested_at.time().isoformat(timespec='minutes'),
                    'date_update': request.updated_at.date().isoformat(),
                    'time_update': request.updated_at.time().isoformat(timespec='minutes'),
                    'duration':request.duration,
                    'description':request.description,
                    'status':request.status
                } for request in request_result],
                'total': total_count,
                'page': request.page,
                'limit': request.limit
            }
        except Exception as e:
            return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                'resp_msg': str(e),
                'resp_data': []
            }
        )

# @transaction_router.get("/{transaction_id}")
# async def get_transaction(transaction_id:uuid.UUID,user_info = Depends(get_current_user)):
#     async with async_session_factory() as session:
#         try:
#             if user_info[1] != '':
#                 raise Exception(user_info[1])
#             user_info=user_info[0]
#             uid_token: str = user_info.get('uid','')
            
#             result = await session.execute(
#                 select(Users).where(Users.uid== uid_token)
#             )
#             user = result.scalar_one_or_none()
#             if not user:
#                 raise Exception("User not found.")
#             role: str = user_info.get('role','')
#             if role != 'admin':
#                 raise Exception("You do not have permission to access this feature.")
#             result = await session.execute(
#                 select(Transactions)
#                 .options(selectinload(Transactions.borrowed_book),selectinload(Transactions.borrow_user))
#                 .where(Transactions.uid == transaction_id))
#             transactions_result = result.scalars().one()
#             if not transactions_result:
#                 raise Exception("Transaction not found.")
#             return {
#                 'resp_msg': "Success.",
#                 'resp_data': {
#                         "borrower": transactions_result.borrow_user.username,
#                         'borrowed_book':transactions_result.borrowed_book.title,
#                         'borrowed_at':transactions_result.borrowed_at,
#                         'returned_at':transactions_result.returned_at,
#                         'due_date':transactions_result.due_date,
#                         "is_overdue":transactions_result.is_overdue
#                 }}
#         except Exception as e:
#             return JSONResponse(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             content = {
#                 'resp_msg': str(e),
#                 'resp_data': None
#             }
#         )
