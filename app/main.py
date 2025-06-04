from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

import startup.db_config as db_config
from api.routes.user import user_router
from api.routes.books import book_router
from api.routes.transaction import transaction_router
from api.routes.review import review_router

# from startup.db_config import init_db



@asynccontextmanager
async def life_span(app:FastAPI):
    print("server is starting...")
    await db_config.init_db()
    yield
    print("server has been stopped")


app = FastAPI(title="Template Core API",
    description="author: MYDEIMOS <3",
    version="0.0.1",
    terms_of_service=None,
    contact=None,
    license_info=None,
    lifespan=life_span)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = exc.errors()
    error_list = []
    for error in details:
        error_list.append(
            {
                "loc": error["loc"],
                "message": error["msg"],
                "type": error["type"],
            }
        )
    modified_response = {
        "resp_data": None,
        "resp_msg": error_list
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(modified_response),
    )

app.include_router(user_router, prefix = "/api/v1/user")
app.include_router(book_router, prefix = "/api/v1/books")
app.include_router(transaction_router, prefix = "/api/v1/transaction")
app.include_router(review_router, prefix = "/api/v1/review")

if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8004, reload=True)  