from datetime import datetime

import pymongo.errors
from bson import ObjectId
from fastapi import APIRouter, HTTPException

import utils
from database import EmployeeDetail
from schemas.userSchemas import EmployeeSchema

router = APIRouter()


@router.post("/add_emp")
async def add_employee_details(payload: EmployeeSchema):
    try:
        existing_employee = EmployeeDetail.find_one({"email": payload.email})
        if not existing_employee:
            employee_details = payload.dict(exclude_unset=True)
            employee_details["emp_id"] = ObjectId()  # Using ObjectId for the emp_id
            employee_details["role"] = "Employee"
            employee_details["password"] = utils.hash_password(payload.password)
            EmployeeDetail.insert_one(employee_details)

            return {"status": "success"}

        else:
            raise HTTPException(status_code=400, detail="Employee with this email already exists")

    except pymongo.errors.DuplicateKeyError:
        return {"status": "failed", "error": "Duplicate emp_id or email."}, 400

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "Error": str(e)}, 500

    except HTTPException as he:
        return {"status": "failed", "message": he.detail}, he.status_code

    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/employee_details")
async def get_employee_details(email: str):
    try:
        if not email or not email.strip():
            raise HTTPException(status_code=400, detail="Invalid User ID")

        details = EmployeeDetail.find_one({"email": email})
        if details:
            del details["_id"]
            del details["password"]
            details["emp_id"] = str(details["emp_id"])
            return {"status": "success", "data": details}
        else:
            return {"status": "failed"}
    except HTTPException as e:
        return {"status": "failed", "error": str(e)}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.patch("/update_employee")
async def update_employee_details(updated_details: EmployeeSchema):
    try:
        existing_details = EmployeeDetail.find_one({"email": updated_details.email})
        if not existing_details:
            raise HTTPException(
                status_code=404,
                detail="Employee details not found."
            )

        # Create data_dict with only the fields not to be excluded
        data_dict = {
            key: value
            for key, value in updated_details.dict().items()
            if key not in ["emp_id", "role", "created_by", "created_at", "role"]
        }

        # Remove any None values from the dictionary
        data_dict = {key: value for key, value in data_dict.items() if value is not None}

        # Add modified_on field
        data_dict["modified_on"] = datetime.now().strftime("%Y-%m-%d")

        filter_query = {"email": updated_details.email}
        update_operation = {"$set": data_dict}
        EmployeeDetail.update_one(filter_query, update_operation)

        return {"status": "success", "message": "Employee details patched."}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/get_all_emp_data")
async def get_all_employment_history():
    try:
        cursor = EmployeeDetail.find({})
        details = [document for document in cursor]

        total_employees = EmployeeDetail.count_documents({})  # Count total employees

        for document in details:
            del document["_id"]
            del document["password"]
            document["emp_id"] = str(document["emp_id"])

        return {"status": "success", "total_employees": total_employees, "data": details}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "Error": str(e)}, 500


@router.delete("/delete_emp")
async def delete_employee(emp_id: str):
    try:
        # Find the employee based on the email address
        existing_employee = EmployeeDetail.find_one({"emp_id": ObjectId(emp_id)})

        if existing_employee:
            # Delete the employee
            EmployeeDetail.delete_one({"emp_id": ObjectId(emp_id)})
            return {"status": "success", "message": "Employee deleted successfully."}
        else:
            raise HTTPException(status_code=404, detail="Employee not found.")

    except HTTPException as he:
        return {"status": "failed", "message": he.detail}, he.status_code
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/emp_details")
async def get_employee_details(emp_id: str):
    try:
        if not emp_id or not emp_id.strip():
            raise HTTPException(status_code=400, detail="Invalid emp ID")

        details = EmployeeDetail.find_one({"emp_id": ObjectId(emp_id)})
        if details:
            del details["_id"]
            details["emp_id"] = str(details["emp_id"])
            return {"status": "success", "data": details}
        else:
            return {"status": "failed"}
    except HTTPException as e:
        return {"status": "failed", "error": str(e)}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
