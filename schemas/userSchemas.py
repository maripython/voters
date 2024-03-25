from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, constr


class UserSignupSchema(BaseModel):
    name: str
    email: EmailStr
    password: constr(min_length=8)
    passwordConfirm: str


class UserSigninSchema(BaseModel):
    email: EmailStr
    password: constr()


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class VerifyOTPSchema(BaseModel):
    email: str
    otp: str


class ResetPasswordSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    passwordConfirm: str


class UpdatePasswordSchema(BaseModel):
    email: EmailStr
    oldPassword: str
    password: constr(min_length=8)
    passwordConfirm: str


class EmployeeSchema(BaseModel):
    emp_id: str
    name: str
    email: EmailStr
    password: constr(min_length=8)
    phone_number: constr(max_length=10)
    role: Optional[str]
    created_by: str
    created_at: Optional[datetime] = datetime.now()
    modified_on: Optional[datetime] = datetime.now()


class TaskSchema(BaseModel):
    task_id: str
    emp_id: str
    name: str
    description: str
    priority: str
    pdf_name: List[str]
    due_date: datetime
    status: str
    modified_by: str
    created_by: str
    created_on: datetime = datetime.now()
    updated_on: datetime = datetime.now()
