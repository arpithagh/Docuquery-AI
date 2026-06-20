import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pdf_processor import process_pdf
from embeddings import embed_and_store, multi_doc_similarity_search, list_documents, delete_document, get_total_chunks
from chat import ask_llm

app = FastAPI(title="DocuQuery AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

conversation_store: dict[str, list[dict]] = {}


class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"
    top_k: int = 5


class DeleteRequest(BaseModel):
    filename: str


@app.get("/")
def root():
    return {"message": "DocuQuery AI API is running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        chunks = process_pdf(str(save_path), file.filename)
        num_stored = embed_and_store(chunks)
        return {
            "message": f"Successfully processed '{file.filename}'",
            "chunks_created": num_stored,
            "filename": file.filename
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/ask")
def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    docs = list_documents()
    if not docs:
        raise HTTPException(status_code=400, detail="No documents uploaded yet.")

    retrieved_chunks = multi_doc_similarity_search(request.question, top_k=request.top_k)

    if not retrieved_chunks:
        return {
            "answer": "I couldn't find any relevant content for your question in the uploaded documents.",
            "sources": [],
            "chunks_used": 0
        }

    history = conversation_store.get(request.session_id, [])
    result  = ask_llm(request.question, retrieved_chunks, history)

    history.append({"role": "user",      "content": request.question})
    history.append({"role": "assistant", "content": result["answer"]})
    conversation_store[request.session_id] = history

    return result


@app.get("/documents")
def get_documents():
    docs         = list_documents()           # [{"name": ..., "chunks": ...}]
    total_chunks = get_total_chunks()
    return {
        "documents":    docs,
        "count":        len(docs),
        "total_chunks": total_chunks
    }


@app.delete("/documents")
def remove_document(request: DeleteRequest):
    delete_document(request.filename)
    return {"message": f"Deleted '{request.filename}'"}


@app.post("/clear-history")
def clear_history(session_id: str = "default"):
    conversation_store.pop(session_id, None)
    return {"message": "Conversation history cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)