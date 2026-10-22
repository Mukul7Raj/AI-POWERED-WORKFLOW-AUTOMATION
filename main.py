import os
import glob
from agent import DocumentWorkflowAgent
from database import get_all_records, get_flagged_records

def print_banner():
    print("=" * 70)
    print("   AI-POWERED WORKFLOW AUTOMATION AGENT (AGENTIC AI)")
    print("   Autonomous Document Ingestion, Schema Validation & Routing")
    print("=" * 70)

def main():
    print_banner()

    agent = DocumentWorkflowAgent(confidence_threshold=0.80)
    docs_folder = os.path.join(os.path.dirname(__file__), "sample_documents")
    files = glob.glob(os.path.join(docs_folder, "*.txt"))

    if not files:
        print(f"[!] No documents found in '{docs_folder}'.")
        return

    print(f"\n[*] Found {len(files)} sample documents to ingest...\n")

    for file_path in sorted(files):
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        agent.process_document(filename, raw_text)

    # Display Database Summary
    print("\n" + "=" * 70)
    print("   DATABASE SUMMARY (POST-PROCESSING)")
    print("=" * 70)
    
    all_records = get_all_records()
    flagged_records = get_flagged_records()

    print(f"\nTotal Ingested: {len(all_records)} | Approved: {len(all_records) - len(flagged_records)} | Flagged for Human Review: {len(flagged_records)}\n")
    
    header = f"{'ID':<4} | {'Vendor':<22} | {'Amount':<12} | {'Conf':<6} | {'Status':<14} | {'File':<18}"
    print(header)
    print("-" * len(header))
    for r in all_records:
        rec = r.to_dict()
        print(f"{rec['id']:<4} | {rec['vendor_name'][:20]:<22} | {rec['total_amount']:<12} | {rec['confidence_score']:<6} | {rec['status']:<14} | {rec['filename']:<18}")

    if flagged_records:
        print("\n" + "!" * 70)
        print(" [HUMAN REVIEW QUEUE] The following records require operator attention:")
        print("!" * 70)
        for r in flagged_records:
            print(f" -> Record #{r.id} ({r.filename}): Reason = {r.extraction_notes}")
            print("    (You can approve or adjust records using the dashboard or database helper)")

if __name__ == "__main__":
    main()
