from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VoterData(BaseModel):
    page_no: str
    pdf_name: str
    data_no: str
    serial_no: str
    voter_id: str
    name: str
    relation: str
    relation_name: str
    gender: str
    age: str
    house_no: str
    image_path: str
    text_data: str
    created_by: str
    modified_by: str
    status: str
    created_on: str
    modified_on: str
