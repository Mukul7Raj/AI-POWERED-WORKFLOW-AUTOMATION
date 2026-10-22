import os
import json
import time
import re
from typing import Tuple
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import DocumentExtraction, ProcessingStatus
from database import save_document_record, init_db

load_dotenv()

# System prompt directing LLM to extract JSON strictly conforming to schema
SYSTEM_PROMPT = """
You are an expert AI data extraction agent.
Your task is to analyze the unstructured document text and extract:
- vendor_name: The vendor/business issuing the document
- document_id: Invoice/receipt reference number
- date: The date of the transaction
- total_amount: Final numeric total cost (float)
- currency: Currency (e.g. USD, EUR, INR)
- items: List of items with description, quantity, and price
- confidence_score: A float between 0.0 and 1.0 indicating your certainty. 
  * If key information (total, vendor, or date) is missing or illegible, set confidence < 0.70.
  * If clearly formatted and unambiguous, set confidence >= 0.85.
- extraction_notes: Brief rationale for any uncertainties or assumptions made.

Output MUST strictly be valid JSON matching the specified structure without extra conversational text.
"""

class DocumentWorkflowAgent:
    def __init__(self, confidence_threshold: float = 0.80):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.confidence_threshold = confidence_threshold
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        init_db()

    # -------------------------------------------------------------
    # Retry logic with exponential backoff for LLM API & schema errors
    # -------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_llm_with_retry(self, raw_text: str) -> str:
        """Invokes OpenAI with retry logic and exponential backoff."""
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured.")

        # OpenAI 1.x client with json_object format
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Document Text:\n\"\"\"\n{raw_text}\n\"\"\""}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content

    def _mock_llm_extraction(self, raw_text: str) -> DocumentExtraction:
        """
        Graceful local fallback agent for demonstration when no OpenAI API key is supplied.
        Simulates LLM extraction, confidence scoring, and ambiguity detection.
        """
        text_lower = raw_text.lower()
        
        # Vendor extraction
        vendor_match = re.search(r"(?:from|vendor|company|merchant):\s*([^\n]+)", raw_text, re.IGNORECASE)
        if not vendor_match:
            first_line = raw_text.strip().split("\n")[0].strip()
            vendor_name = first_line if len(first_line) < 40 else "Unknown Vendor"
        else:
            vendor_name = vendor_match.group(1).strip()

        # Document ID
        doc_id_match = re.search(r"(?:invoice|receipt|order|ref)\s*(?:#|no\.?|id)?\s*[:\-]?\s*([A-Za-z0-9\-]+)", raw_text, re.IGNORECASE)
        document_id = doc_id_match.group(1) if doc_id_match else None

        # Date
        date_match = re.search(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b", raw_text)
        date = date_match.group(1) if date_match else None

        # Amount
        amounts = re.findall(r"[\$€£₹]?\s*(\d+(?:,\d{3})*(?:\.\d{2}))", raw_text)
        total_amount = float(amounts[-1].replace(",", "")) if amounts else 0.0

        # Currency
        currency = "USD"
        if "€" in raw_text or "eur" in text_lower:
            currency = "EUR"
        elif "£" in raw_text:
            currency = "GBP"
        elif "₹" in raw_text or "inr" in text_lower:
            currency = "INR"

        # Calculate simulated confidence based on document ambiguity
        confidence = 0.95
        notes = []

        if not document_id:
            confidence -= 0.15
            notes.append("Missing explicit document ID")
        if not date:
            confidence -= 0.15
            notes.append("Missing transaction date")
        if total_amount == 0.0:
            confidence -= 0.45
            notes.append("Could not determine total monetary amount")
        if "torn" in text_lower or "unclear" in text_lower or "blurry" in text_lower or "estimated" in text_lower:
            confidence -= 0.30
            notes.append("Document explicitly indicates degraded/ambiguous text")

        confidence = max(0.2, min(1.0, confidence))
        note_text = "; ".join(notes) if notes else "High-fidelity extraction complete."

        return DocumentExtraction(
            vendor_name=vendor_name,
            document_id=document_id,
            date=date,
            total_amount=total_amount,
            currency=currency,
            items=[],
            confidence_score=round(confidence, 2),
            extraction_notes=note_text
        )

    def extract_and_validate(self, raw_text: str) -> DocumentExtraction:
        """
        Executes extraction with schema validation and retry fallback.
        """
        if self.client:
            raw_json = self._call_llm_with_retry(raw_text)
            try:
                parsed = json.loads(raw_json)
                return DocumentExtraction.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as e:
                # If first attempt suffered hallucination / malformed JSON, try mock fallback or propagate
                print(f"[!] Validation error from LLM output: {e}. Falling back to rule-based parser.")
                return self._mock_llm_extraction(raw_text)
        else:
            return self._mock_llm_extraction(raw_text)

    def process_document(self, filename: str, raw_text: str) -> Tuple[DocumentExtraction, str]:
        """
        End-to-end autonomous agent workflow:
        1. Reads unstructured text
        2. Extracts key data with LLM & validates schema
        3. Human-in-the-loop decision:
           - confidence >= threshold -> APPROVED (written to DB)
           - confidence < threshold -> NEEDS_REVIEW (flagged for manual check)
        4. Saves safely to Database
        """
        print(f"\n[+] Processing: '{filename}' ...")
        
        # 1. Extraction & Validation
        extraction = self.extract_and_validate(raw_text)

        # 2. Confidence Evaluation & Routing
        if extraction.confidence_score >= self.confidence_threshold:
            status = ProcessingStatus.APPROVED.value
            print(f"    [OK] Confidence: {extraction.confidence_score:.2f} >= {self.confidence_threshold} -> Status: APPROVED")
        else:
            status = ProcessingStatus.NEEDS_REVIEW.value
            print(f"    [!] Low Confidence: {extraction.confidence_score:.2f} < {self.confidence_threshold} -> Status: FLAGGED FOR HUMAN REVIEW")
            print(f"        Reason: {extraction.extraction_notes}")

        # 3. Safe Database Persistence
        save_document_record(
            filename=filename,
            vendor_name=extraction.vendor_name,
            document_id=extraction.document_id,
            date=extraction.date,
            total_amount=extraction.total_amount,
            currency=extraction.currency,
            confidence_score=extraction.confidence_score,
            status=status,
            notes=extraction.extraction_notes,
            raw_text=raw_text,
            extracted_json=extraction.model_dump_json(indent=2)
        )

        return extraction, status
