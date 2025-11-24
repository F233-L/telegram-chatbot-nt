# rag_api.py - RAG local + Groq Llama 3.1 (gratis y funcional)
import os
import re
from typing import List, Dict, Set

from pypdf import PdfReader
from groq import Groq

# ===========================
# CONFIG
# ===========================

PDF_PATH = "documento.pdf"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "PONE_TU_KEY_DE_GROQ_AQUI")

if GROQ_API_KEY.startswith("PONE_TU_KEY"):
    raise ValueError("Configura tu GROQ_API_KEY antes de ejecutar el bot.")

client = Groq(api_key=GROQ_API_KEY)

# Estado del RAG en memoria
CHUNKS: List[str] = []
CHUNK_TOKENS: List[Set[str]] = []
_INITIALIZED = False

# Regex simple para separar palabras
WORD_RE = re.compile(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+")


# ===========================
# UTILIDADES PDF
# ===========================

def _read_pdf(pdf_path: str) -> str:
    """Lee el PDF completo y devuelve su texto."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"No encontré el archivo PDF: {pdf_path}")

    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _split_text(text: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
    """Divide el texto en pedazos con solapamiento."""
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _tokenize(text: str) -> Set[str]:
    """Convierte un texto en conjunto de palabras normalizadas."""
    return set(WORD_RE.findall(text.lower()))


def _ensure_initialized():
    """Carga el PDF y prepara el RAG UNA sola vez."""
    global _INITIALIZED, CHUNKS, CHUNK_TOKENS

    if _INITIALIZED:
        return

    print("Inicializando RAG local (sin embeddings externos)...")

    text = _read_pdf(PDF_PATH)
    CHUNKS = _split_text(text)
    CHUNK_TOKENS = [_tokenize(chunk) for chunk in CHUNKS]

    _INITIALIZED = True
    print(f"Fragmentos generados: {len(CHUNKS)}")


# ===========================
# RANKING LOCAL DE FRAGMENTOS
# ===========================

def _rank_chunks(question: str, k: int = 4) -> List[str]:
    """Encuentra los fragmentos más parecidos usando coincidencia de palabras."""
    q_tokens = _tokenize(question)

    if not q_tokens:
        return CHUNKS[:k]

    puntajes = []
    for idx, tokens in enumerate(CHUNK_TOKENS):
        score = len(q_tokens & tokens)  # intersección de palabras
        puntajes.append((score, idx))

    puntajes.sort(reverse=True, key=lambda x: x[0])

    top = [CHUNKS[i] for score, i in puntajes[:k] if score > 0]

    return top if top else CHUNKS[:k]


# ===========================
# LLAMADA A GROQ
# ===========================

def _call_groq(prompt: str) -> str:
    """Envía el prompt a Groq usando Llama 3.1 y devuelve texto."""
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    # PRESTAR ATENCIÓN: el objeto es .message.content
    return completion.choices[0].message.content


# ===========================
# INTERFAZ FINAL PARA TELEGRAM
# ===========================

def get_answer_from_pdf(
    question: str,
    history: List[Dict[str, str]],
    k: int = 4
) -> str:
    """Combina el RAG local + llamada Groq para responder al usuario."""
    _ensure_initialized()

    contexto_docs = _rank_chunks(question, k)
    contexto_texto = "\n\n".join(contexto_docs)

    prompt = (
        "Eres un chatbot conectado a un documento PDF del alumno.\n"
        "Debes responder EXCLUSIVAMENTE con la información del documento.\n"
        "Si no aparece en el PDF, dilo explícitamente.\n\n"
        "=== CONTEXTO ===\n"
        f"{contexto_texto}\n"
        "=== FIN CONTEXTO ===\n\n"
        f"Pregunta del usuario: {question}\n"
        "Responde en español, de manera clara y directa."
    )

    return _call_groq(prompt).strip()
