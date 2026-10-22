from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

# ---------------------------------------------------------
# 1. Pydantic Models (LLM Extraction & Validation Schema)
# ---------------------------------------------------------
class LineItem(BaseModel):
    description: str = Field(description="Name or description of the purchased item/service")
    quantity: int = Field(default=1, description="Quantity of item")
    price: float = Field(description="Unit price or item cost")

class DocumentExtraction(BaseModel):
    vendor_name: str = Field(description="Name of the company or vendor issuing the document")
    document_id: Optional[str] = Field(default=None, description="Invoice or receipt number if visible")
    date: Optional[str] = Field(default=None, description="Date on the document in YYYY-MM-DD or readable format")
    total_amount: float = Field(description="Final total monetary amount")
    currency: str = Field(default="USD", description="Currency symbol or 3-letter code (e.g. USD, EUR, INR)")
    items: List[LineItem] = Field(default_factory=list, description="List of line items")
    confidence_score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the extraction between 0.0 (uncertain) and 1.0 (certain)"
    )
    extraction_notes: Optional[str] = Field(default="", description="Reasons for confidence score or ambiguities detected")

# ---------------------------------------------------------
# 2. SQLAlchemy Models (Database Storage: SQLite / PostgreSQL)
# ---------------------------------------------------------
Base = declarative_base()

class ProcessingStatus(str, enum.Enum):
    APPROVED = "APPROVED"          # High confidence, safely written to DB
    NEEDS_REVIEW = "NEEDS_REVIEW"  # Low confidence, flagged for human review
    REJECTED = "REJECTED"          # Human reviewed and rejected

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    vendor_name = Column(String(255), nullable=False)
    document_id = Column(String(100), nullable=True)
    date = Column(String(50), nullable=True)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    confidence_score = Column(Float, nullable=False)
    status = Column(String(50), default=ProcessingStatus.APPROVED.value)
    extraction_notes = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=False)
    extracted_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "vendor_name": self.vendor_name,
            "document_id": self.document_id,
            "total_amount": f"{self.total_amount:.2f} {self.currency}",
            "confidence_score": round(self.confidence_score, 2),
            "status": self.status,
            "notes": self.extraction_notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
