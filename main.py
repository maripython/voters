from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import auth, employeeDetails, pdf_filter, emp_task, test1

# openai.api_key = ["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"]


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [settings.CLIENT_ORIGIN, "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(employeeDetails.router, prefix="/api/employee_details", tags=["Employee Details"])
    app.include_router(pdf_filter.router, prefix="/api/filter_details", tags=["Filter Details"])
    app.include_router(emp_task.router, prefix="/api/task", tags=["Employee Task"])
    app.include_router(test1.router, prefix="/api/test", tags=["test"])

except Exception as e:
    print(f"Error while including routers: {e}")


@app.get("/")
async def health_checker():
    return {"status": "success"}
