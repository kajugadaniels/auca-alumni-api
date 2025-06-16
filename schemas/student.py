from pydantic import BaseModel

class StudentSchema(BaseModel):
    id: int
    id_number: int
    first_name: str
    last_name: str

    class Config:
        orm_mode = True
