# Referred to tutorial on how to build FastAPI app:
# https://www.youtube.com/watch?v=398DuQbQJq0&t=22s&ab_channel=EricRoby
from sqlalchemy import create_engine, Column, Integer, Text, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

# pip install pgvector
from pgvector.sqlalchemy import Vector # https://github.com/pgvector/pgvector-python/issues/74

URL_DATABASE = "postgresql://postgres:ilagan123@localhost:5432/satdata"

# Connect to the database
engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class satdata(Base):
    __tablename__ = "satdata" 

    id = Column(Integer, primary_key=True, index=True)
    case_url = Column(Text)
    case_title = Column(Text)
    citation_number = Column(Text)
    case_year = Column(Text)
    case_act = Column(Text)
    case_topic = Column(Text, index=True)
    member = Column(Text)
    heard_date = Column(Date)
    delivery_date = Column(Date)
    file_no = Column(Text)
    case_between = Column(Text)
    catchwords = Column(Text)
    legislations = Column(Text)
    result = Column(Text)
    category = Column(Text)
    representation = Column(Text)
    referred_cases = Column(Text)
    reasons = Column(Text)
    reasons_summary = Column(Text)
    reasons_summary_embedding = Column(Vector(768))

class reasons_chunks(Base):
    __tablename__ = "reasons_chunks" 

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("satdata.id", ondelete="CASCADE"))
    case_topic = Column(Text)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    chunk_embedding = Column(Vector(768))

class uploaded_docs(Base):
    __tablename__ = "uploaded_docs" 
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Text)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    chunk_embedding = Column(Vector(768))