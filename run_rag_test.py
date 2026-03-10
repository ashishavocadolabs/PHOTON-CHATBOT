from pipelines.ingestion_pipeline import ingest_directory
from core.rag_engine import rag_engine

print("doc store path", rag_engine.doc_store.path)
print("Before ingestion docs", len(rag_engine.doc_store.ids))

# quick PDF inspect
try:
    from PyPDF2 import PdfReader
    r = PdfReader("knowledge/photon_docs/Doc1.pdf")
    print("pdf pages", len(r.pages))
    for idx,p in enumerate(r.pages[:3]):
        print(f"text page {idx}:", repr(p.extract_text()))
    print("...skipping remaining pages...")
except Exception as e:
    print("pdf read error", e)

new_store = ingest_directory("knowledge/photon_docs", rag_engine.doc_store.path)
print("After ingestion (new store) docs", len(new_store.ids))
# sync the global store
rag_engine.doc_store = new_store
print("After ingestion (global) docs", len(rag_engine.doc_store.ids))

answer = rag_engine.query("Summarize the document", top_k_docs=3)
print("RAG answer:\n", answer)

# test typo correction
typo_ans = rag_engine.query("EHO ARE YOU")
print("typo query answer:\n", typo_ans)

# test ai_orchestrator small talk
from core.ai_orchestrator import handle_chat
print("small talk - how are you:", handle_chat("how are you"))
print("small talk - who are you:", handle_chat("who are you"))
print("small talk - you know me:", handle_chat("you know me"))

print("script done")
