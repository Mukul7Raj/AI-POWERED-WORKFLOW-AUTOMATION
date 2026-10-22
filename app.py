import streamlit as st
import pandas as pd
from agent import DocumentWorkflowAgent
from database import get_all_records, get_flagged_records, update_record_status, init_db
from models import ProcessingStatus

st.set_page_config(page_title="AI Workflow Automation Agent", page_icon="⚡", layout="wide")

init_db()
agent = DocumentWorkflowAgent(confidence_threshold=0.80)

st.title("⚡ AI-Powered Workflow Automation Agent")
st.caption("Agentic AI • Unstructured Document Extraction • Structured Validation • Human-in-the-Loop Routing")

tab1, tab2, tab3 = st.tabs(["📊 Ingestion Dashboard", "⚠️ Human Review Queue", "📤 Ingest New Document"])

# Tab 1: Dashboard
with tab1:
    st.subheader("Database Overview")
    records = get_all_records()
    if not records:
        st.info("No records in database yet. Process a document to begin.")
    else:
        df = pd.DataFrame([r.to_dict() for r in records])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Processed", len(df))
        approved_count = len(df[df["status"] == ProcessingStatus.APPROVED.value])
        flagged_count = len(df[df["status"] == ProcessingStatus.NEEDS_REVIEW.value])
        col2.metric("Approved (Direct to DB)", approved_count)
        col3.metric("Flagged for Review", flagged_count)

        st.dataframe(df, use_container_width=True)

# Tab 2: Human Review Queue
with tab2:
    st.subheader("Human Review Queue (Low Confidence Items)")
    flagged = get_flagged_records()
    
    if not flagged:
        st.success("🎉 All documents have met confidence criteria! Queue is clear.")
    else:
        for item in flagged:
            with st.expander(f"Review Record #{item.id} - {item.vendor_name} ({item.filename})", expanded=True):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown("**Original Raw Document Text:**")
                    st.code(item.raw_text, language="text")
                with col_b:
                    st.markdown("**Extracted Data & Risk Flags:**")
                    st.write(f"- **Confidence Score:** `{item.confidence_score:.2f}`")
                    st.write(f"- **Detected Total:** `{item.total_amount:.2f} {item.currency}`")
                    st.write(f"- **Document ID:** `{item.document_id or 'N/A'}`")
                    st.write(f"- **Date:** `{item.date or 'N/A'}`")
                    st.warning(f"**Flag Reason:** {item.extraction_notes}")

                    bcol1, bcol2 = st.columns(2)
                    if bcol1.button("✅ Approve Record", key=f"app_{item.id}"):
                        update_record_status(item.id, ProcessingStatus.APPROVED.value, notes="Approved by human reviewer")
                        st.success(f"Record #{item.id} approved!")
                        st.rerun()
                    if bcol2.button("❌ Reject Record", key=f"rej_{item.id}"):
                        update_record_status(item.id, ProcessingStatus.REJECTED.value, notes="Rejected due to invalid information")
                        st.error(f"Record #{item.id} marked as rejected.")
                        st.rerun()

# Tab 3: Upload/Ingest
with tab3:
    st.subheader("Process a New Document")
    sample_text = st.text_area(
        "Paste invoice/receipt text here:",
        height=180,
        placeholder="Paste plain text invoice or receipt here..."
    )
    doc_name = st.text_input("Document Name / Identifier:", value="manual_upload.txt")

    if st.button("🚀 Run Automation Agent", type="primary"):
        if sample_text.strip():
            with st.spinner("Agent running extraction, validation, and confidence scoring..."):
                extraction, status = agent.process_document(doc_name, sample_text)
                if status == ProcessingStatus.APPROVED.value:
                    st.success(f"Document processed and APPROVED! (Confidence: {extraction.confidence_score:.2f})")
                else:
                    st.warning(f"Document FLAGGED FOR REVIEW (Confidence: {extraction.confidence_score:.2f}). Reason: {extraction.extraction_notes}")
                st.json(extraction.model_dump())
        else:
            st.warning("Please provide text to process.")
