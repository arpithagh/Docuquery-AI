import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a helpful document assistant. Answer questions based ONLY on the provided context from the user's documents.

Rules:
- Only use information from the context below
- If the answer is not in the context, say "I couldn't find that in the uploaded documents"
- Be accurate and grounded — never invent facts not present in the context

Response style:
- For simple factual questions ("what is X", "how many", "when"), give a direct, concise answer in 1-3 sentences.
- For questions asking "why", "how", "explain", or about challenges, benefits, features, causes, or concepts:
  - Use bullet points, one per distinct idea
  - Give a short 1-2 sentence explanation under each bullet, not just a label
  - Do not just list terms — explain what each one means or why it matters
- Use markdown formatting (bullet points, **bold** for key terms) to make answers easy to scan
- Keep the overall tone clear and professional, avoid unnecessary repetition"""


def build_context(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not retrieved_chunks:
        return "No relevant context found."

    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(
            f"[Source: {chunk['source']} | Relevance: {chunk['similarity']}]\n{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


def ask_llm(
    question: str,
    retrieved_chunks: list[dict],
    conversation_history: list[dict] = None
) -> dict:
    """
    Send question + context to Groq LLM.
    
    conversation_history: list of {"role": "user"/"assistant", "content": "..."} 
                          for multi-turn memory
    
    Returns dict with answer and sources used.
    """
    context = build_context(retrieved_chunks)

    # Build the user message with injected context
    user_message = f"""Context from documents:
{context}

Question: {question}"""

    # Build messages list with optional history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        # Include last 6 turns of history to stay within token limits
        messages.extend(conversation_history[-6:])

    messages.append({"role": "user", "content": user_message})

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,  # slightly higher for more natural explanatory tone
        max_tokens=1536
    )

    answer = response.choices[0].message.content

    # Extract unique sources cited
    sources_used = list({chunk["source"] for chunk in retrieved_chunks})

    return {
        "answer": answer,
        "sources": sources_used,
        "chunks_used": len(retrieved_chunks)
    }