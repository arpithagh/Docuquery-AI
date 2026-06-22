import streamlit as st
import requests
import uuid
import re
import os

API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
if API_URL and not API_URL.startswith("http"):
    # Render gives a bare host -> needs https; Docker compose sets a full http:// URL already
    use_https = os.environ.get("BACKEND_USE_HTTPS", "true").lower() == "true"
    API_URL = f"{'https' if use_https else 'http'}://{API_URL}"


def md_to_html(text: str) -> str:
    """Convert simple markdown (bold, bullets, line breaks) to HTML for the chat bubble."""
    # Bold: **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    lines = text.split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        is_bullet = stripped.startswith("- ") or stripped.startswith("* ") or re.match(r"^\d+\.\s", stripped)

        if is_bullet:
            if not in_list:
                html_parts.append("<ul style='margin:6px 0;padding-left:20px'>")
                in_list = True
            content = re.sub(r"^(-|\*|\d+\.)\s+", "", stripped)
            html_parts.append(f"<li style='margin-bottom:4px'>{content}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if stripped:
                html_parts.append(f"<p style='margin:6px 0'>{stripped}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "".join(html_parts)

st.set_page_config(
    page_title="DocuQuery AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: var(--background-color); }
[data-testid="stSidebar"] { background: #f8f9fa; border-right: 1px solid #e9ecef; }
[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem; }
.block-container { padding: 1.5rem 2rem !important; }

.logo { display:flex; align-items:center; gap:10px; margin-bottom:1.2rem; }
.logo-icon { width:34px; height:34px; background:#185FA5; border-radius:8px;
             display:flex; align-items:center; justify-content:center;
             font-size:18px; flex-shrink:0; }
.logo-text { font-size:16px; font-weight:600; color:#1a1a2e; line-height:1.2; }
.logo-sub  { font-size:11px; color:#6c757d; }

.upload-label { font-size:12px; font-weight:500; color:#6c757d;
                text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; }

.doc-card { display:flex; align-items:center; gap:10px;
            background:#fff; border:1px solid #e9ecef; border-radius:10px;
            padding:10px 12px; margin-bottom:6px; }
.doc-icon-wrap { width:32px; height:32px; border-radius:7px; background:#e8f0fe;
                 display:flex; align-items:center; justify-content:center;
                 font-size:16px; flex-shrink:0; }
.doc-info { flex:1; min-width:0; }
.doc-name { font-size:12px; font-weight:600; color:#1a1a2e;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.doc-meta { font-size:11px; color:#6c757d; margin-top:1px; }

.stats-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:12px 0; }
.stat-box  { background:#fff; border:1px solid #e9ecef; border-radius:10px;
             padding:10px 12px; text-align:center; }
.stat-val  { font-size:20px; font-weight:700; color:#185FA5; }
.stat-lbl  { font-size:11px; color:#6c757d; margin-top:2px; }

.section-hdr { font-size:11px; font-weight:600; color:#6c757d;
               text-transform:uppercase; letter-spacing:.06em;
               margin:14px 0 6px; }

.model-badge { display:inline-flex; align-items:center; gap:5px;
               background:#e8f5e9; color:#2e7d32; font-size:11px;
               font-weight:500; padding:3px 10px; border-radius:20px; }
.live-dot { width:6px; height:6px; background:#43a047;
            border-radius:50%; display:inline-block;
            animation:pulse 1.8s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.chat-wrap { display:flex; flex-direction:column; gap:14px; padding:4px 0 16px; }

.bubble-row { display:flex; gap:10px; align-items:flex-start; }
.bubble-row.user { flex-direction:row-reverse; }

.avatar { width:28px; height:28px; border-radius:50%; flex-shrink:0;
          display:flex; align-items:center; justify-content:center;
          font-size:11px; font-weight:600; margin-top:2px; }
.avatar.user { background:#185FA5; color:#fff; }
.avatar.ai   { background:#e8f5e9; color:#2e7d32; font-size:14px; }

.bubble { max-width:80%; }
.bubble-text { font-size:13.5px; line-height:1.65; color:#1a1a2e;
               background:#fff; border:1px solid #e9ecef;
               border-radius:14px; padding:10px 14px; }
.bubble-row.user .bubble-text { background:#185FA5; color:#fff;
                                 border-color:#185FA5; border-radius:14px 4px 14px 14px; }
.bubble-row.ai  .bubble-text  { border-radius:4px 14px 14px 14px; }
.bubble-text.out-of-scope      { color:#6c757d; font-style:italic; background:#f8f9fa; }

.bubble-meta { display:flex; align-items:center; gap:6px;
               flex-wrap:wrap; margin-top:5px; padding:0 2px; }
.source-pill { display:inline-flex; align-items:center; gap:4px;
               background:#e8f0fe; color:#185FA5; font-size:11px;
               font-weight:500; padding:2px 8px; border-radius:20px; }
.chunk-note  { font-size:11px; color:#adb5bd; }

.empty-state { text-align:center; padding:48px 24px; color:#6c757d; }
.empty-state .empty-icon { font-size:48px; margin-bottom:12px; }
.empty-state h3 { font-size:15px; font-weight:600; color:#1a1a2e; margin-bottom:6px; }
.empty-state p  { font-size:13px; line-height:1.6; }

.divider { border:none; border-top:1px solid #e9ecef; margin:12px 0; }

#MainMenu, footer, header { visibility:hidden; }
[data-testid="stFileUploadDropzone"] { border:1.5px dashed #ced4da !important;
                                        border-radius:10px !important;
                                        background:#fafafa !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "documents" not in st.session_state:
    st.session_state.documents = []

if "total_chunks" not in st.session_state:
    st.session_state.total_chunks = 0

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []


# ── API helpers ────────────────────────────────────────────
def fetch_documents():
    try:
        r = requests.get(f"{API_URL}/documents", timeout=5)
        data = r.json()
        st.session_state.documents    = data.get("documents", [])
        st.session_state.total_chunks = data.get("total_chunks", 0)
    except Exception:
        st.session_state.documents    = []
        st.session_state.total_chunks = 0


def upload_pdf(file):
    try:
        r = requests.post(
            f"{API_URL}/upload",
            files={"file": (file.name, file.getvalue(), "application/pdf")},
            timeout=60
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def ask_question(question, top_k=5):
    try:
        r = requests.post(
            f"{API_URL}/ask",
            json={
                "question": question,
                "session_id": st.session_state.session_id,
                "top_k": top_k
            },
            timeout=60
        )
        if r.status_code != 200:
            return {"error": f"Backend Error {r.status_code}: {r.text}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_doc(filename):
    try:
        requests.delete(f"{API_URL}/documents", json={"filename": filename}, timeout=10)
    except Exception:
        pass


def clear_history():
    st.session_state.messages = []
    try:
        requests.post(f"{API_URL}/clear-history",
                      params={"session_id": st.session_state.session_id})
    except Exception:
        pass


# ── Initial fetch ──────────────────────────────────────────
fetch_documents()


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:

    st.markdown(
        '<div class="logo">'
        '<div class="logo-icon">📚</div>'
        '<div>'
        '<div class="logo-text">DocuQuery AI</div>'
        '<div class="logo-sub">Chat with your documents</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Upload ──
    st.markdown('<div class="upload-label">Upload document</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")

    if uploaded and uploaded.name not in st.session_state.uploaded_files:
        with st.spinner(f"Indexing {uploaded.name}..."):
            result = upload_pdf(uploaded)

        if "error" in result:
            st.error(f"Failed: {result['error']}")
        else:
            st.session_state.uploaded_files.append(uploaded.name)
            st.success(f"✅ {result.get('chunks_created', 0)} chunks indexed")
            fetch_documents()

    # ── Stats ──
    st.markdown(
        '<div class="stats-row">'
        '<div class="stat-box">'
        f'<div class="stat-val">{len(st.session_state.documents)}</div>'
        '<div class="stat-lbl">documents</div>'
        '</div>'
        '<div class="stat-box">'
        f'<div class="stat-val">{st.session_state.total_chunks}</div>'
        '<div class="stat-lbl">chunks indexed</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Document list ──
    if st.session_state.documents:
        st.markdown('<div class="section-hdr">Indexed documents</div>', unsafe_allow_html=True)
        for doc in st.session_state.documents:
            name   = doc["name"] if isinstance(doc, dict) else doc
            chunks = doc.get("chunks", "?") if isinstance(doc, dict) else "?"
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    '<div class="doc-card">'
                    '<div class="doc-icon-wrap">📄</div>'
                    '<div class="doc-info">'
                    f'<div class="doc-name" title="{name}">{name}</div>'
                    f'<div class="doc-meta">{chunks} chunks</div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.write("")
                if st.button("🗑", key=f"del_{name}", help=f"Remove {name}"):
                    delete_doc(name)
                    if name in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.remove(name)
                    fetch_documents()
                    st.rerun()
    else:
        st.info("No documents yet. Upload a PDF above.")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Settings ──
    st.markdown('<div class="section-hdr">Settings</div>', unsafe_allow_html=True)
    top_k = st.slider("Chunks to retrieve", 1, 10, 5,
                       help="More chunks = richer context but slower response")

    if st.button("🗑️ Clear chat history", use_container_width=True):
        clear_history()
        st.rerun()

    if st.button("🔄 Reset all documents", use_container_width=True):
        try:
            r = requests.post(f"{API_URL}/reset", timeout=10)
            if r.status_code == 200:
                st.session_state.messages = []
                st.session_state.documents = []
                st.session_state.total_chunks = 0
                st.session_state.uploaded_files = []
                st.success("✅ All documents cleared")
                st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px;color:#adb5bd;line-height:1.6">'
        '<b>Stack:</b> FastAPI · ChromaDB<br>'
        'sentence-transformers · Groq'
        '</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════
# MAIN — header
# ══════════════════════════════════════════════════════════════
col_title, col_badge = st.columns([3, 1])
with col_title:
    st.markdown("### 💬 Chat with your documents")
with col_badge:
    st.markdown(
        '<div style="text-align:right;padding-top:6px">'
        '<span class="model-badge">'
        '<span class="live-dot"></span> Llama 3.3 70B'
        '</span>'
        '</div>',
        unsafe_allow_html=True
    )

st.markdown('<hr style="border:none;border-top:1px solid #e9ecef;margin:0 0 12px">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAIN — messages
# ══════════════════════════════════════════════════════════════
if not st.session_state.messages:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon">🔍</div>'
        '<h3>Ask anything about your documents</h3>'
        '<p>Upload a PDF in the sidebar, then ask questions.<br>'
        'Answers are grounded in your documents — no hallucinations.</p>'
        '</div>',
        unsafe_allow_html=True
    )
else:
    chat_html = '<div class="chat-wrap">'
    for msg in st.session_state.messages:
        role = msg["role"]
        text = msg["content"]
        sources      = msg.get("sources", [])
        chunks_used  = msg.get("chunks_used", 0)
        out_of_scope = "couldn't find" in text.lower() or "not in the uploaded" in text.lower()

        if role == "user":
            chat_html += (
                '<div class="bubble-row user">'
                '<div class="avatar user">You</div>'
                '<div class="bubble">'
                f'<div class="bubble-text">{text}</div>'
                '</div>'
                '</div>'
            )
        else:
            bubble_cls = "bubble-text out-of-scope" if out_of_scope else "bubble-text"
            meta_html = ""
            if sources and not out_of_scope:
                pills = "".join(f'<span class="source-pill">📄 {s}</span>' for s in sources)
                meta_html = (
                    '<div class="bubble-meta">'
                    f'{pills}'
                    f'<span class="chunk-note">{chunks_used} chunks retrieved</span>'
                    '</div>'
                )
            chat_html += (
                '<div class="bubble-row ai">'
                '<div class="avatar ai">🤖</div>'
                '<div class="bubble">'
                f'<div class="{bubble_cls}">{md_to_html(text)}</div>'
                f'{meta_html}'
                '</div>'
                '</div>'
            )

    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAIN — input
# ══════════════════════════════════════════════════════════════
prompt = st.chat_input("Ask anything about your documents…")

if prompt:
    if not st.session_state.documents:
        st.warning("⚠️ Please upload at least one PDF first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Searching through your documents…"):
            result = ask_question(prompt, top_k)

        if "error" in result:
            answer      = f"Connection error: {result['error']}. Is the backend running?"
            sources     = []
            chunks_used = 0
        else:
            answer      = result.get("answer", "No answer returned.")
            sources     = result.get("sources", [])
            chunks_used = result.get("chunks_used", 0)

        st.session_state.messages.append({
            "role":        "assistant",
            "content":     answer,
            "sources":     sources,
            "chunks_used": chunks_used
        })
        st.rerun()