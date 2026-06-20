import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    words = text.split()
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)
        if len(chunk_words) > 10:
            chunks.append({"text": chunk_text_str, "chunk_index": chunk_index})
            chunk_index += 1
        start += chunk_size - overlap

    return chunks


def process_pdf(pdf_path: str, filename: str) -> list[dict]:
    text = extract_text_from_pdf(pdf_path)

    if not text.strip():
        raise ValueError(f"No text found in {filename}.")

    chunks = chunk_text(text)

    for chunk in chunks:
        chunk["source"] = filename
        chunk["pdf_path"] = pdf_path

    return chunks