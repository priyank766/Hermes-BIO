"""Mechanism-of-action explainer. One Gemini call per candidate, cached in the DB."""
import logging
from google import genai
from google.genai import types
from ..config import settings

log = logging.getLogger(__name__)

PROMPT = """You are a medicinal-chemistry tutor. Given a drug candidate and its target protein, write a concise mechanism-of-action explanation in 3–5 sentences.

Cover:
1. What the protein does in the disease.
2. How the molecule is believed to interact with it (binding mode, key chemistry).
3. The therapeutic consequence.

Stay precise. No marketing language. If the molecule is FDA-approved, mention its established class. If novel, say so. Do not output JSON or markdown — plain prose only."""


def explain_mechanism(
    target_uniprot: str,
    target_name: str,
    disease: str,
    smiles: str,
    drug_name: str | None,
    is_approved: bool,
    binding_affinity: float,
) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    user = (
        f"Disease: {disease}\n"
        f"Target: {target_name} (UniProt {target_uniprot})\n"
        f"Drug: {drug_name or 'unnamed compound'} ({'FDA-approved' if is_approved else 'novel'})\n"
        f"SMILES: {smiles}\n"
        f"Predicted binding affinity: {binding_affinity:.2f} kcal/mol\n"
    )
    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=user)])],
            config=types.GenerateContentConfig(
                system_instruction=PROMPT,
                temperature=0.3,
            ),
        )
        return (resp.text or "").strip()
    except Exception as e:
        log.exception("explain failed")
        return f"(explanation unavailable: {e})"
