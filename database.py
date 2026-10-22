import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base, DocumentRecord, ProcessingStatus

load_dotenv()

# Default to local SQLite, or use PostgreSQL connection string from environment
# Example PostgreSQL: postgresql://postgres:password@localhost:5432/workflow_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///workflow_agent.db")

engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes tables in database (SQLite or PostgreSQL)."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Context session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_document_record(
    filename: str, 
    vendor_name: str, 
    document_id: str, 
    date: str, 
    total_amount: float, 
    currency: str, 
    confidence_score: float, 
    status: str, 
    notes: str, 
    raw_text: str, 
    extracted_json: str
) -> DocumentRecord:
    """Inserts a processed document record into the database."""
    session = SessionLocal()
    try:
        record = DocumentRecord(
            filename=filename,
            vendor_name=vendor_name,
            document_id=document_id,
            date=date,
            total_amount=total_amount,
            currency=currency,
            confidence_score=confidence_score,
            status=status,
            extraction_notes=notes,
            raw_text=raw_text,
            extracted_json=extracted_json
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
    finally:
        session.close()

def get_all_records():
    """Fetches all documents ordered by newest first."""
    session = SessionLocal()
    try:
        return session.query(DocumentRecord).order_by(DocumentRecord.id.desc()).all()
    finally:
        session.close()

def get_flagged_records():
    """Fetches documents requiring human review."""
    session = SessionLocal()
    try:
        return session.query(DocumentRecord).filter_by(status=ProcessingStatus.NEEDS_REVIEW.value).all()
    finally:
        session.close()

def update_record_status(record_id: int, new_status: str, notes: str = None):
    """Allows human reviewer to approve or reject a flagged record."""
    session = SessionLocal()
    try:
        record = session.query(DocumentRecord).filter_by(id=record_id).first()
        if record:
            record.status = new_status
            if notes:
                record.extraction_notes = f"{record.extraction_notes or ''} [Reviewer: {notes}]"
            session.commit()
            return True
        return False
    finally:
        session.close()
