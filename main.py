from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Union
import databases
from sqlalchemy import create_engine, Column, String, Table, MetaData
from passlib.context import CryptContext
from fastapi.openapi.utils import get_openapi
import yaml

DATABASE_URL = "sqlite:///./test.db"
SECRET_KEY = "password-secret-key"
PASSWORD_HASH_ALGORITHM = "bcrypt"

database = databases.Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True),
    Column("company_name", String, nullable=True),
    Column("f_name", String),
    Column("l_name", String),
    Column("email", String, unique=True, nullable=True),
    Column("password", String, nullable=True),
    Column("mobile", String, nullable=True),
    Column("hashtag", String, nullable=True),
    Column("dob", String, nullable=True),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI()

class UserBase(BaseModel):
    f_name: str
    l_name: str
    mobile: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    hashtag: Optional[str] = None
    dob: Optional[str] = None

class Form1(UserBase):
    company_name: str
    email: EmailStr
    password: str

class Form2(UserBase):
    mobile: str
    hashtag: str

class Form3(UserBase):
    mobile: str
    dob: str

class UpdateUser(BaseModel):
    company_name: Optional[str] = None
    f_name: Optional[str] = None
    l_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    mobile: Optional[str] = None
    hashtag: Optional[str] = None
    dob: Optional[str] = None

class UserOut(BaseModel):
    id: str
    f_name: str
    l_name: str
    mobile: Optional[str]
    company_name: Optional[str]
    email: Optional[EmailStr]
    hashtag: Optional[str]
    dob: Optional[str]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

async def generate_uuid():
    query = users.select()
    users_count = len(await database.fetch_all(query))
    return str(users_count + 1)

def hash_password(password: str):
    return pwd_context.hash(password)

@app.post("/add_user", response_model=UserOut)
async def create_user(user: Union[Form1, Form2, Form3] = Body(...)):

    query = users.select().where(users.c.email == user.email)
    existing_user = await database.fetch_one(query)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Insert new user
    query = users.insert().values(
        id=await generate_uuid(),
        company_name=user.company_name,
        f_name=user.f_name,
        l_name=user.l_name,
        email=user.email,
        password=hash_password(user.password),
        mobile=user.mobile,
        hashtag=user.hashtag,
        dob=user.dob,
    )
    await database.execute(query)
    return user

@app.get("/get_user/{user_id}", response_model=UserOut)
async def get_user(user_id: str):
    query = users.select().where(users.c.id == user_id)
    user = await database.fetch_one(query)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/get_users", response_model=List[UserOut])
async def get_users():
    query = users.select()
    return await database.fetch_all(query)

@app.patch("/update_user/{user_id}", response_model=UserOut)
async def update_user(user_id: str, user: UpdateUser):
    query = users.update().where(users.c.id == user_id).values(**user.dict(exclude_unset=True))
    await database.execute(query)
    updated_user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.delete("/delete_user/{user_id}")
async def delete_user(user_id: str):
    query = users.delete().where(users.c.id == user_id)
    await database.execute(query)
    return {"message": "User deleted"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Dyanamic User Flow API Documentation",
        version="1.0.0",
        description="This is the API documentation for the Dyanamic User Flow API. It provides endpoints to create, read, update and delete users.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

openapi_schema = custom_openapi()

with open("api_documentation.yaml", "w") as yaml_file:
    yaml.dump(openapi_schema, yaml_file)
