import pymongo.errors
import pymongo.errors
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from database import EmployeeDetail, TaskDetail, db
from schemas.userSchemas import TaskSchema

router = APIRouter()


@router.post("/assign_task")
async def assign_task(task: TaskSchema):
    try:
        employee = EmployeeDetail.find_one({"emp_id": ObjectId(task.emp_id)})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Insert the task into the database
        task_details = task.dict(exclude_unset=True)
        task_details["task_id"] = ObjectId()  # Using ObjectId for the task_id
        task_details["emp_id"] = ObjectId(employee['emp_id'])  # Assigning emp_id to emp_id
        task_details["due_date"] = task.due_date.strftime("%Y-%m-%d")  # Format due_date
        task_details["status"] = "progress"
        TaskDetail.insert_one(task_details)

        return {"status": "success", "message": "Task assigned successfully."}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except HTTPException as he:
        return {"status": "failed", "message": he.detail}, he.status_code
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/get_employee_tasks")
async def get_employee_tasks(emp_id: str):
    try:
        # Find tasks based on the emp_id
        tasks = list(TaskDetail.find({"emp_id": ObjectId(emp_id)}))

        # Extract unique PDF names from the tasks
        pdf_names_set = set()
        for task in tasks:
            pdf_names_set.update(task.get("pdf_name", []))

        pdf_names = list(pdf_names_set)  # Convert set to list

        return {"status": "success", "emp_id": emp_id, "pdf_names": pdf_names}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500

    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.patch("/update_task")
async def update_task(task_id: str, updated_task: TaskSchema):
    try:
        # Find the task based on the task_id
        existing_task = TaskDetail.find_one({"task_id": ObjectId(task_id)})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Update the task details
        updated_values = updated_task.dict(exclude_unset=True)
        for key, value in updated_values.items():
            if key not in ["task_id", "emp_id", "created_by", "created_on"]:
                existing_task[key] = value

        # Save the updated task
        TaskDetail.replace_one({"task_id": ObjectId(task_id)}, existing_task)

        return {"status": "success", "message": "Task updated successfully."}

    except HTTPException as he:
        return {"status": "failed", "message": he.detail}, he.status_code
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/assigned_tasks")
async def get_assigned_tasks(emp_id: str):
    try:
        cursor = TaskDetail.find({"emp_id": ObjectId(emp_id)})
        tasks = [task for task in cursor]

        formatted_tasks = []
        for task in tasks:
            formatted_task = {
                "task_id": str(task.get("task_id", "")),
                "emp_id": str(task.get("emp_id", "")),
                "description": task.get("description", ""),
                "priority": task.get("priority", ""),
                "pdf_name": task.get("pdf_name", []),
                "due_date": task.get("due_date", ""),
                "status": task.get("status", ""),
                "name": task.get("name", "")
            }
            formatted_tasks.append(formatted_task)

        return {"status": "success", "data": formatted_tasks}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/get_data")
async def get_data(emp_id: str):
    try:
        details_list = TaskDetail.find({"emp_id": ObjectId(emp_id)})
        details = list(details_list)
        details_count = len(details)  # Count the number of details
        # Count the number of tasks with "progress" and "completed" statuses
        progress_count = TaskDetail.count_documents({"emp_id": ObjectId(emp_id), "status": "progress"})
        completed_count = TaskDetail.count_documents({"emp_id": ObjectId(emp_id), "status": "completed"})

        response_data = []

        # Collect unique pdf_names and their respective counts
        unique_pdf_names = set()  # To store unique pdf names
        response_counts = {
            "total_tasks": details_count,
            "progress_count": progress_count,
            "completed_count": completed_count,
            "pdf_name": unique_pdf_names
        }
        for detail in details:
            pdf_name_list = detail.get("pdf_name", [])  # Ensure pdf_name is a list
            unique_pdf_names.update(pdf_name_list)  # Add pdf names to the set

        # Iterate over unique pdf names
        for pdf_name in unique_pdf_names:
            if not pdf_name:
                continue
            collection = db[pdf_name]
            query = {}

            # Fetch data from the database for the current pdf_name
            data_from_db = list(collection.find(query))
            if data_from_db:
                # Convert ObjectId to string for JSON serialization
                for item in data_from_db:
                    for key, value in item.items():
                        if isinstance(value, ObjectId):
                            item[key] = str(value)

                response_data.extend(data_from_db)

        if response_data:
            return {"counts": response_counts, "data": response_data}
        else:
            return {"message": "No data found for the provided employee id"}, 404

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500


@router.delete("/delete_task")
async def delete_task(task_id: str):
    try:
        # Check if the task exists
        existing_task = TaskDetail.find_one({"task_id": ObjectId(task_id)})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Delete the task
        TaskDetail.delete_one({"task_id": ObjectId(task_id)})

        return {"status": "success", "message": "Task deleted successfully."}

    except HTTPException as he:
        return {"status": "failed", "message": he.detail}, he.status_code
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/task_details")
async def get_task_details(task_id: str):
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(status_code=400, detail="Invalid User ID")

        details = TaskDetail.find_one({"task_id": ObjectId(task_id)})
        if details:
            del details["_id"]
            del details["emp_id"]
            details["task_id"] = str(details["task_id"])
            return {"status": "success", "data": details}
        else:
            return {"status": "failed"}
    except HTTPException as e:
        return {"status": "failed", "error": str(e)}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.get("/emp_task_details")
async def get_emp_task_details(emp_id: str):
    try:
        if not emp_id:
            raise HTTPException(status_code=400, detail="Invalid Task IDs")

        task_details = []
        for emp_ids in emp_id:
            if not emp_ids or not emp_ids.strip():
                raise HTTPException(status_code=400, detail="Invalid Task ID")

            details = TaskDetail.find_one({"emp_id": ObjectId(emp_ids)})
            if details:
                del details["_id"]
                details["emp_id"] = str(details["emp_id"])
                details["task_id"] = str(details["task_id"])
                task_details.append(details)

        if task_details:
            return {"status": "success", "data": task_details}
        else:
            return {"status": "failed", "error": "No task details found"}

    except HTTPException as e:
        return {"status": "failed", "error": str(e)}
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# list pdf
@router.get("/get_emp_pdf")
async def get_emp_pdf(emp_id: str):
    try:
        details_list = TaskDetail.find({"emp_id": ObjectId(emp_id)})
        details = list(details_list)
        unique_pdf_names = set()  # To store unique pdf names
        pdf_list = {
            "pdf_name": unique_pdf_names
        }
        for detail in details:
            pdf_name_list = detail.get("pdf_name", [])  # Ensure pdf_name is a list
            unique_pdf_names.update(pdf_name_list)
        return {"data": pdf_list}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500


@router.get("/emp_count")
async def get_emp_count(emp_id: str):
    try:
        details_list = TaskDetail.find({"emp_id": ObjectId(emp_id)})
        details = list(details_list)

        details_count = len(details)  # Count the number of details
        progress_count = TaskDetail.count_documents({"emp_id": ObjectId(emp_id), "status": "progress"})
        completed_count = TaskDetail.count_documents({"emp_id": ObjectId(emp_id), "status": "completed"})

        pdf_list = {
            "total_tasks": details_count,
            "progress_count": progress_count,
            "completed_count": completed_count,
        }
        return pdf_list

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500
