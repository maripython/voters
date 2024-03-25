from http.client import HTTPException
from typing import Optional, List

import pandas as pd
import pymongo.errors
from bson import ObjectId
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from database import db, FirstPageData, TaskDetail
from schemas.voter_schemas import VoterData

router = APIRouter()


# list all pdfs from db
@router.get("/list_pdf")
async def get_collections():
    try:
        collections = db.list_collection_names()
        collections = [collection for collection in collections if
                       collection not in ["users", "employeedetail", "first_page_data", "task_detail"]]
        return {"collections": collections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/all_pdf_data/", response_model=List[dict])
async def get_data(pdf_name: str):
    try:
        collection = db[pdf_name]
        query = {}

        data_from_db = list(collection.find(query))

        if data_from_db:
            data_from_db = [item for item in data_from_db if item.get("status") != "new"]
            for item in data_from_db:
                for key, value in item.items():
                    if isinstance(value, ObjectId):
                        item[key] = str(value)
            return data_from_db
        else:
            return {"message": "PDF Not Found"}, 404
    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"message": str(e)}, 500


# filter based on status
@router.get("/status_filter/")
async def filter_data(pdf_name: str, status: str = None, voter_id: str = None):
    try:
        collection = db[pdf_name]

        pipeline = []

        if status:
            pipeline.append({"$match": {"status": status}})

        if voter_id:
            pipeline.append({"$match": {"voter_id": voter_id}})

        pipeline.append({"$project": {"_id": 0}})  # Exclude _id field

        data = list(collection.aggregate(pipeline))

        # Counting the data based on the filter criteria
        count_pipeline = pipeline.copy()
        count_pipeline.append({"$count": "total"})
        count_result = list(collection.aggregate(count_pipeline))
        count = count_result[0]["total"] if count_result else 0

        return {"count": count, "data": data}
    except Exception as e:
        return {"error": str(e)}


# fetch document count like processed_pdf and completed_documents
@router.get("/count")
async def count_documents_in_db():
    try:
        collections = db.list_collection_names()
        completed_count = 0
        partially_completed_count = 0
        collection_count = 0  # Variable to count the number of collections

        for collection_name in collections:
            if collection_name not in ["users", "employeedetail", "first_page_data", "task_detail"]:
                collection = db[collection_name]
                collection_count += 1  # Increment the collection count
                completed_count += collection.count_documents({"status": "completed"})
                partially_completed_count += collection.count_documents({"status": "partially completed"})

        return {
            "processed_pdf": collection_count,
            "completed_documents": completed_count,
            "partially_completed_documents": partially_completed_count,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/get_task_details")
async def get_tasks():
    try:
        # Retrieve all tasks from the collection
        tasks = list(TaskDetail.find({}))
        # Count total tasks
        total_tasks = TaskDetail.count_documents({})

        # Convert tasks to a more suitable format for response
        tasks = [{k: str(v) if isinstance(v, ObjectId) else v for k, v in task.items() if
                  k not in ('_id', 'created_on', 'updated_on')} for task in tasks]

        # Count tasks by status
        status_counts = {
            "progress": TaskDetail.count_documents({"status": "progress"}),
            "completed": TaskDetail.count_documents({"status": "completed"}),
            "total_count": total_tasks
        }

        return {"status": "success", "status_counts": status_counts, "data": tasks}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500

    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


@router.get("/get_document")
async def get_document(pdf_name: str = Query(..., description="Name of the PDF document"),
                       serial_no: str = Query(..., description="Serial number of the document")):
    try:
        # Retrieve the document from MongoDB based on pdf_name and serial_no
        collection = db[pdf_name]
        document = collection.find_one({"serial_no": serial_no})

        # Check if the document exists
        if document is None:
            raise HTTPException(status_code=404,
                                detail=f"Document with 'serial_no' {serial_no} in PDF '{pdf_name}' not found.")

        # Convert ObjectId to string for JSON serialization
        document['_id'] = str(document['_id'])

        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/update_document/")
async def update_document(pdf_name: str, new_data: VoterData):
    try:
        collection = db[pdf_name]
        number = new_data.serial_no

        # Check if serial_no is provided
        if not number:
            raise HTTPException(status_code=400, detail="Field 'serial_no' is required in the provided data.")

        # Exclude certain fields from update
        data_dict = {key: value for key, value in new_data.dict(exclude_unset=True).items() if
                     key not in ["serial_no", "pdf_name", "data_no", "page_no", "image_path", "text_data", "created_by",
                                 "created_on"]}

        # Update the document based on serial_no
        result = collection.update_one({"serial_no": number}, {"$set": data_dict})

        # Check if document is updated
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No document found for the provided serial number.")

        return {"message": "Document updated successfully."}
    except HTTPException as e:
        # Re-raise HTTPException to maintain status code and details
        raise e
    except Exception as e:
        # Handle other exceptions and return 500 status code with error details
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_data(pdf_name: str, status: Optional[str] = None):
    try:
        # Get first page data
        first_page_data = FirstPageData.find_one({"pdf_name": pdf_name})
        del first_page_data["_id"]
        del first_page_data["first_page_path"]
        del first_page_data["text_path"]
        # Get data from database
        if not first_page_data:
            raise HTTPException(status_code=404, detail="pdf not found")

        details = first_page_data.get("pdf_name", "")
        if details:
            collection = db[details]
            query = {} if status is None else {"status": status}

            # Retrieve data based on the provided status
            data_from_db = list(collection.find(query))

            # Filter out documents with status "new"
            data_from_db = [item for item in data_from_db if item.get("status") != "new"]

            if data_from_db:
                for item in data_from_db:
                    # Convert ObjectId to string if present in the item
                    for key, value in item.items():
                        if isinstance(value, ObjectId):
                            item[key] = str(value)

                    # Remove fields not needed for export
                    fields_to_delete = {"cropped_image_path", "status", "image_path", "created_on", "data_no",
                                        "text_data", "text_path", "first_page_path", "modified_on", "modified_by"}
                    for field in fields_to_delete:
                        item.pop(field, None)

                # Create DataFrame from data_from_db
                db_df = pd.DataFrame(data_from_db)

                # Repeat first_page_data for each row in data_from_db
                repeated_first_page_data = pd.DataFrame([first_page_data] * len(data_from_db))

                # Merge first_page_data DataFrame with db_df DataFrame
                result_df = pd.concat([repeated_first_page_data.reset_index(drop=True),
                                       db_df.reset_index(drop=True)], axis=1)

                # Export DataFrame to Excel
                file_name = f"static/{pdf_name}_export.xlsx"
                result_df.to_excel(file_name, index=False)

                return FileResponse(file_name, filename=file_name)

        return {"status": "failed", "error": "No data found"}

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500


# retrieve data by district and state
@router.get("/district")
async def get_data(district: str, assembly: Optional[str] = None):
    try:
        query = {"district": district}
        if assembly:
            query["assembly_constituency"] = assembly

        details_list = FirstPageData.find(query)
        details = list(details_list)
        response_counts = []
        pdf_names = []
        response_data = []

        # Collect pdf_names and their respective counts
        pdf_counts = {}
        for detail in details:
            pdf_name = detail.get("pdf_name", "")
            if not pdf_name:
                continue
            collection = db[pdf_name]
            query = {}
            data_count = collection.count_documents(query)
            pdf_counts[pdf_name] = data_count

        # Retrieve all data for pdf_names with counts
        for pdf_name, data_count in pdf_counts.items():
            collection = db[pdf_name]
            # data_from_db = list(collection.find({}, {"_id": 0}))
            response_counts.append({"pdf_name": pdf_name, "data_count": data_count})
            pdf_names.append(pdf_name)
            # response_data.append({"data": data_from_db})

        if response_counts:
            return {"counts": response_counts, "pdf_names": pdf_names}
        else:
            return {"status": "failed", "message": "No data found for the provided district and assembly"}, 404

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500


# retrieve data by district
# @router.get("/get_data_by_district")
async def get_data_by_district(district: str):
    try:
        details_list = FirstPageData.find({"district": district})
        details = list(details_list)
        response_counts = []
        response_data = []

        # Collect pdf_names and their respective counts
        pdf_counts = {}
        for detail in details:
            pdf_name = detail.get("pdf_name", "")
            if not pdf_name:
                continue
            collection = db[pdf_name]
            query = {}
            data_count = collection.count_documents(query)
            pdf_counts[pdf_name] = data_count

        # Retrieve all data for pdf_names with counts
        for pdf_name, data_count in pdf_counts.items():
            collection = db[pdf_name]
            data_from_db = list(collection.find({}, {"_id": 0}))
            response_counts.append({"pdf_name": pdf_name, "data_count": data_count})
            response_data.append({"pdf_name": pdf_name, "data": data_from_db})

        if response_counts:
            return {"counts": response_counts, "data": response_data}
        else:
            return {"message": "No data found for the provided district"}, 404

    except pymongo.errors.PyMongoError as e:
        return {"status": "failed", "error": str(e)}, 500
    except Exception as e:
        return {"message": str(e)}, 500


@router.patch("/update_document_db")
async def update_document_db(pdf_name: str, new_data: VoterData):
    try:
        collection = db[pdf_name]
        number = new_data.serial_no

        if not number:
            raise HTTPException(status_code=400, detail="Field 'serial_no' is required in the provided data.")

        # Convert new_data to a dictionary for MongoDB update
        data_dict = {key: value for key, value in new_data.dict(exclude_unset=True).items() if
                     key not in ["serial_no", "pdf_name", "data_no", "page_no", "image_path", "text_data", "created_by",
                                 "created_on"]}
        if len(data_dict["voter_id"]) == 10:
            existing_docs = collection.count_documents({"voter_id": new_data.voter_id})
            print(new_data.voter_id)
            print(existing_docs)
            if existing_docs == 1 or existing_docs == 0:
                result = collection.update_one({"serial_no": number}, {"$set": data_dict})
                if result.modified_count == 0:
                    raise HTTPException(status_code=404, detail="No documents were updated.")
                else:
                    return {"status": "success", "detail": "Document updated successfully."}
            elif existing_docs >= 2:
                return {"status": "success", "detail": "Document is duplicate."}
        else:
            return {"status": "failed", "detail": "Enter Voter ID correctly..."}
    except HTTPException:
        raise  # Re-raise the HTTPException
    except Exception as e:
        return str(e)
