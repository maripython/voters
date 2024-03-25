from pymongo import MongoClient
from config import settings

client = MongoClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)

try:
    conn = client.server_info()
    print(f'Connected to MongoDB {conn.get("version")}')
except Exception:
    print("Unable to connect MongoDB Server.")

db = client[settings.MONGO_INITDB_DATABASE]
Users = db.users
EmployeeDetail = db.employeedetail
FirstPageData = db.first_page_data
TaskDetail = db.task_detail
