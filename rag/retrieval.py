"""
Unified Retrieval and Question Answering Pipeline.

Supports:
- Individual Document Search
- Workspace Search
- Strict source citations (filename, page/sheet, row/line)
- Gemini API generation with fallback to deterministic grounded answering
- Privacy checks preventing transmission of private documents without approval
"""

from typing import List, Dict, Any, Optional
from rag.vector_store import vector_store
from auth.gemini_client import (
    call_gemini_generate,
    get_gemini_api_key,
    get_gemini_model
)


def retrieve_context(
    user_id: int,
    query: str,
    target_doc_id: Optional[str] = None,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """Retrieves relevant chunks with exact source references from ephemeral ChromaDB."""
    return vector_store.search(
        user_id=user_id,
        query=query,
        target_doc_id=target_doc_id,
        top_k=top_k
    )


def generate_rag_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    user_consented_to_cloud: bool = False,
    is_demo_mode: bool = False
) -> Dict[str, Any]:
    """
    Synthesizes an answer using retrieved chunks as strict context.
    Calls Gemini API if available and permitted, or falls back to deterministic grounded answering.
    Preserves all source citations.
    """
    if not retrieved_chunks:
        return {
            "answer": "No relevant document evidence found in the active workspace.",
            "citations": [],
            "source_count": 0,
            "engine": "local_fallback"
        }

    # Format citations
    citations = []
    context_lines = []
    for idx, c in enumerate(retrieved_chunks, start=1):
        citations.append({
            "source_id": idx,
            "filename": c["filename"],
            "location": c["location"],
            "excerpt": c["text"][:250] + ("..." if len(c["text"]) > 250 else "")
        })
        context_lines.append(f"[Source {idx}] File: {c['filename']} ({c['location']}):\n{c['text']}")

    context_str = "\n\n".join(context_lines)
    api_key = get_gemini_api_key()
    model = get_gemini_model()

    # If Gemini API key is configured AND privacy rules allow (either user consented OR demo mode)
    if api_key and (user_consented_to_cloud or is_demo_mode):
        system_instruction = (
            "You are a privacy-first academic document intelligence assistant.\n"
            "Answer the user question strictly using the provided document excerpts.\n"
            "Cite the specific [Source N] in your answer whenever stating facts.\n"
            "If the excerpts do not contain the answer, state honestly that the document does not mention it.\n"
            "Do not invent facts or cite non-existent sources."
        )

        user_prompt = (
            f"User Question: {query}\n\n"
            f"Document Context:\n{context_str}\n\n"
            f"Please answer concisely and accurately based strictly on the context above."
        )

        gemini_result = call_gemini_generate(
            prompt=user_prompt,
            system_instruction=system_instruction,
            api_key=api_key,
            model=model,
            user_approved_external_processing=user_consented_to_cloud,
            is_demo_document=is_demo_mode
        )

        if gemini_result["success"]:
            return {
                "answer": gemini_result["text"],
                "citations": citations,
                "source_count": len(citations),
                "engine": f"Gemini ({gemini_result['model_used']})"
            }
        else:
            # If Gemini call failed (e.g. rate limit, invalid key), append explanation and use deterministic fallback
            fallback_answer = _build_deterministic_answer(retrieved_chunks, note=f"(Gemini API error: {gemini_result['error']})")
            return {
                "answer": fallback_answer,
                "citations": citations,
                "source_count": len(citations),
                "engine": "local_fallback_on_error",
                "api_error": gemini_result["error"]
            }

    # Deterministic offline grounded summary
    notice = "(Privacy Active: Using local engine. To enable Gemini synthesis, check Cloud Processing Consent in Chat / Settings.)" if not user_consented_to_cloud and not is_demo_mode else "(Generated locally: Configure GEMINI_API_KEY to enable cloud AI synthesis.)"
    fallback_answer = _build_deterministic_answer(retrieved_chunks, note=notice)
    return {
        "answer": fallback_answer,
        "citations": citations,
        "source_count": len(citations),
        "engine": "local_deterministic"
    }


def _build_deterministic_answer(retrieved_chunks: List[Dict[str, Any]], note: str = "") -> str:
    """Builds a deterministic factual excerpt list from retrieved chunks."""
    summary_bullets = "\n".join([f"• From **{c['filename']}** ({c['location']}): {c['text'][:150]}..." for c in retrieved_chunks[:3]])
    text = f"Based on the retrieved document context:\n\n{summary_bullets}"
    if note:
        text += f"\n\n*{note}*"
    return text
