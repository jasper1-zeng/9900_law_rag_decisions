# Referred to tutorial on how to build FastAPI app:
# https://www.youtube.com/watch?v=398DuQbQJq0&t=22s&ab_channel=EricRoby
# https://stackoverflow.com/questions/71235905/fastapi-to-read-from-an-existing-database-table-in-postgresql

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
from database import Base, engine, SessionLocal, satdata, reasons_chunks
from sqlalchemy.orm import Session
from datetime import date

class satdataSchema(BaseModel):
    id: int
    case_url: str | None = None
    case_title: str | None = None
    citation_number: str | None = None
    case_year: str | None = None
    case_act: str | None = None
    case_topic: str | None = None
    member: str | None = None
    heard_date: date | None = None
    delivery_date: date | None = None
    file_no: str | None = None
    case_between: str | None = None
    catchwords: str | None = None
    legislations: str | None = None
    result: str | None = None
    category: str | None = None
    representation: str | None = None
    referred_cases: str | None = None
    reasons: str | None = None
    reasons_summary: str | None = None
    reasons_summary_embedding : list[float]

class reasonschunksSchema(BaseModel):
    id : int
    case_id : int
    case_topic : str | None = None
    chunk_index : int
    chunk_text : str | None = None
    chunk_embedding: list[float]

class uploadeddocsSchema(BaseModel):
    id : int
    document_id : str | None = None
    chunk_index : int
    chunk_text : str | None = None
    chunk_embedding: list[float]

Base.metadata.create_all(bind=engine)
app = FastAPI()

# Create connection to the database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# Create API endpoints

########################################################################################################################
### APIs for satdata table ###

# Fetch all cases from satdata table
@app.get("/cases/", response_model=List[satdataSchema])
async def get_all_cases(db: db_dependency):
    return db.query(satdata).all()

# Fetch a single case by citation_number from satdata table
@app.get("/cases/{citation_number}", response_model=satdataSchema)
async def get_case(citation_number: str, db: db_dependency):
    case = db.query(satdata).filter(satdata.citation_number == citation_number).first()
    # Case where the case doesn't exist
    if not case:
        raise HTTPException(status_code=404, detail="Case is not found")
    return case

# Fetch all cases under certain topic from satdata table
@app.get("/cases/topic/{case_topic}", response_model=List[satdataSchema])
async def search_cases(topic: str, db: db_dependency):
    return db.query(satdata).filter((satdata.case_topic.ilike(f"%{topic}%")) ).all()

# Fetch all cases by year from satdata table
@app.get("/cases/year/{case_year}", response_model=List[satdataSchema])
async def search_cases(case_year: str, db: db_dependency):
    return db.query(satdata).filter(satdata.case_year == case_year).all()

########################################################################################################################
### APIs for satdata table ###

# Fetch all chunks from reasons_chunks table by case_id
@app.get("/cases/{case_id}/chunks", response_model=List[reasonschunksSchema])
async def get_chunks(case_id: int, db: db_dependency):
    return db.query(reasons_chunks).filter(reasons_chunks.case_id == case_id).all()

# Fetch all chunks from reasons_chunks table by case_topic
@app.get("/cases/topic/{case_topic}/chunks", response_model=List[reasonschunksSchema])
async def get_chunks(case_topic: str, db: db_dependency):
    return db.query(reasons_chunks).filter((reasons_chunks.case_topic.ilike(f"%{case_topic}%")) ).all()

########################################################################################################################
### APIs for uploaded_docs table ###
