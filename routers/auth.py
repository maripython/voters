import hashlib
from datetime import datetime, timedelta
from random import randbytes
from typing import Annotated

import pymongo.errors
import stripe
from fastapi import APIRouter, HTTPException, status, Response, Depends, Body

import utils
from config import settings
# from database import Feedback
from database import Users, EmployeeDetail
from emails.verifyEmail import VerifyEmail, ForgotPassEmail
from oauth2 import AuthJWT
from schemas.userSchemas import UserSignupSchema, UserSigninSchema, ForgotPasswordSchema, \
    ResetPasswordSchema, UpdatePasswordSchema

router = APIRouter()

# Replace with your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/signup")
async def signup_user(payload: UserSignupSchema):
    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match"
        )
    existing = Users.find_one({"email": payload.email})

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )
    user_info = payload.dict()
    del user_info["passwordConfirm"]
    user_info["role"] = "admin"
    user_info["verified"] = False
    user_info["status"] = "active"
    user_info["username"] = None
    user_info["created_at"] = datetime.utcnow()
    user_info["updated_at"] = user_info["created_at"]
    user_info["password"] = utils.hash_password(payload.password)
    result = Users.insert_one(user_info)
    new_user = Users.find_one({"_id": result.inserted_id})

    try:
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        verification_code = hashedCode.hexdigest()
        Users.find_one_and_update(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "verification_code": verification_code,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        print(token.hex())
        await VerifyEmail(
            new_user["name"], token.hex(), [payload.email]
        ).sendVerificationCode()
    except Exception as error:
        print(error)
        Users.find_one_and_update(
            {"_id": result.inserted_id},
            {"$set": {"verification_code": None, "updated_at": datetime.utcnow()}},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error sending email",
        )
    return {
        "status": "success",
        "message": "Verification token successfully sent to your email",
    }


ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post("/signin_api")
async def users_signin(payload: UserSigninSchema, response: Response, Authorize: AuthJWT = Depends()):
    # Check if the user exists
    db_user = Users.find_one({"email": payload.email})
    print(db_user)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect Email",
        )

    # Check password length
    if len(payload.password) < 8:
        response.status_code = status.HTTP_200_OK
        return {"detail": "Password must be at least 8 characters long"}

    else:
        if not utils.verify_password(payload.password, db_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect Password",
            )

        if db_user["status"] == "inactive":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is not active, please contact the administrator",
            )

    # Create access token
    access_token = Authorize.create_access_token(
        subject=str(db_user["_id"]),
        expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN),
    )

    # Create refresh token
    refresh_token = Authorize.create_refresh_token(
        subject=str(db_user["_id"]),
        expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN),
    )

    # Store refresh and access tokens in cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    print("Access Token Cookie:", response.headers["set-cookie"])

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRES_IN * 60,
        expires=REFRESH_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="logged_in",
        value="True",
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )

    return {
        "access_token": access_token,
        "name": db_user.get("name", ""),
        "role": db_user.get("role", ""),
        # "verified": db_user.get("verified", False),
        "email": db_user.get("email", ""),
        "emp_id": str(db_user["_id"]),
    }


@router.post("/logout")
async def user_logout(response: Response, Authorize: AuthJWT = Depends()):
    try:
        try:
            Authorize.jwt_required()

        except Exception as e:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"message": "Invalid token", "error": str(e)}

        # If the user is authenticated, proceed with logout
        user_id = Authorize.get_jwt_subject()

        if user_id:
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            response.delete_cookie("logged_in")

            return {"message": "Logout successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No login event found for the user",
            )
    except HTTPException as e:
        print("HTTPException:", e)  # Add this line for debugging
        return {"message": "Logout failed", "error": str(e)}
    except Exception as ex:
        print("Exception:", ex)  # Add this line for debugging
        return {"message": "Internal server error"}


@router.patch("/verify")
async def verify_email(code: Annotated[str, Body(..., embed=True)]):
    try:
        hashedCode = hashlib.sha256()
        hashedCode.update(bytes.fromhex(code))
        verification_code = hashedCode.hexdigest()
        result = Users.find_one_and_update(
            {"verification_code": verification_code},
            {
                "$set": {
                    "verification_code": verification_code,
                    "verified": True,
                    "updated_at": datetime.utcnow(),
                }
            },
            new=True,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid verification code",
            )
        return {"status": "success", "message": "Verified Successfully"}
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verification code. Please double-check and try again",
        )


@router.post("/forgotPass")
async def forgot_pass(payload: ForgotPasswordSchema):
    if payload.email == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Email"
        )
    existing = Users.find_one({"email": payload.email})
    if existing:
        try:
            token = randbytes(10)
            hashedCode = hashlib.sha256()
            hashedCode.update(token)
            verification_code = hashedCode.hexdigest()
            Users.find_one_and_update(
                {"email": payload.email},
                {
                    "$set": {
                        "verification_code": verification_code,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            print(token.hex())
            await ForgotPassEmail(
                existing["name"], token.hex(), [payload.email]
            ).sendVerificationCode()
        except Exception as error:
            print(error)
            Users.find_one_and_update(
                {"email": payload.email},
                {"$set": {"verification_code": None, "updated_at": datetime.utcnow()}},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error sending email",
            )
    return {
        "status": "success",
        "message": "Password reset code successfully sent to your email",
    }


@router.post("/resetPass")
async def reset_pass(payload: ResetPasswordSchema):
    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match"
        )
    existing = Users.find_one({"email": payload.email})
    if existing:
        user_info = payload.dict()
        user_info["password"] = utils.hash_password(payload.password)
        try:
            Users.find_one_and_update(
                {"email": payload.email},
                {
                    "$set": {
                        "password": user_info["password"],
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as error:
            print(error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error in reset password",
            )
    return {
        "status": "success",
        "message": "Password reset done successfully",
    }


@router.post("/updatePass")
async def reset_pass(payload: UpdatePasswordSchema):
    if len(payload.oldPassword.strip()) <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Old Password should not be empty"
        )
    elif len(payload.password.strip()) <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password should not be empty"
        )
    elif payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match"
        )
    existing = Users.find_one({"email": payload.email})
    if existing:
        user_info = payload.dict()

        if not utils.verify_password(payload.oldPassword, existing["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid old password"
            )
        user_info["password"] = utils.hash_password(payload.password)
        try:
            Users.find_one_and_update(
                {"email": payload.email},
                {
                    "$set": {
                        "password": utils.hash_password(payload.password),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as error:
            print(error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error in reset password",
            )
    return {
        "status": "success",
        "message": "Password updated successfully",
    }


@router.post("/signin")
async def users_signin(payload: UserSigninSchema, response: Response, Authorize: AuthJWT = Depends()):
    try:
        # Check if the user exists
        db_user = Users.find_one({"email": payload.email})
        if not db_user:
            db_user = EmployeeDetail.find_one({"email": payload.email})
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect Email",
                )

        # Check password length
        if len(payload.password) < 8:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"detail": "Password must be at least 8 characters long"}

        # Verify password
        if not utils.verify_password(payload.password, db_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect Password",
            )

        # Check user status
        if db_user.get("status") == "inactive":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is not active, please contact the administrator",
            )

        # Create access token
        access_token = Authorize.create_access_token(
            subject=str(db_user["_id"]),
            expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN),
        )

        # Create refresh token
        refresh_token = Authorize.create_refresh_token(
            subject=str(db_user["_id"]),
            expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN),
        )

        # Store refresh and access tokens in cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
            expires=ACCESS_TOKEN_EXPIRES_IN * 60,
            path="/",
            domain=None,
            secure=True,
            httponly=True,
            samesite="none",
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRES_IN * 60,
            expires=REFRESH_TOKEN_EXPIRES_IN * 60,
            path="/",
            domain=None,
            secure=True,
            httponly=True,
            samesite="none",
        )

        response.set_cookie(
            key="logged_in",
            value="True",
            max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
            expires=ACCESS_TOKEN_EXPIRES_IN * 60,
            path="/",
            domain=None,
            secure=True,
            httponly=True,
            samesite="none",
        )

        return {
            "access_token": access_token,
            "name": db_user.get("name", ""),
            "role": db_user.get("role", ""),
            "verified": db_user.get("verified", False),
            "email": db_user.get("email", ""),
            "id": str(db_user["_id"]),
            "emp_id": str(db_user.get("emp_id", "")),
        }
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500
