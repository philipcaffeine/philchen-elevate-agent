"""Policy Q&A Retrieval Tool over Altostrat Singapore Policy Handbook (OKF)."""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from .. import config

SIMILARITY_THRESHOLD = 0.65


def _get_knowledge_dir() -> Path:
    k_dir = Path(config.KNOWLEDGE_DIR)
    if not k_dir.exists():
        alt = Path(__file__).resolve().parent.parent / "knowledge"
        if alt.exists():
            return alt
    return k_dir


def _parse_markdown_file(file_path: Path) -> Dict[str, Any]:
    """Parse YAML frontmatter and body from markdown concept file."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            except Exception:
                pass

    return {
        "frontmatter": frontmatter,
        "body": body,
        "raw": text,
    }


def list_concepts() -> Dict[str, List[Dict[str, str]]]:
    """List all available HR policy concept documents in the knowledge repository."""
    k_dir = _get_knowledge_dir()
    concepts = []
    if not k_dir.exists():
        return {"concepts": []}

    for p in sorted(k_dir.rglob("*.md")):
        if p.name in ("index.md", "log.md"):
            continue
        parsed = _parse_markdown_file(p)
        fm = parsed.get("frontmatter", {})
        rel_id = str(p.relative_to(k_dir)).removesuffix(".md")
        concepts.append({
            "id": rel_id,
            "title": fm.get("title", p.stem.replace("-", " ").title()),
            "description": fm.get("description", ""),
        })
    return {"concepts": concepts}


def read_concept(concept_id: str) -> Dict[str, Any]:
    """Read full content and citations for a given concept ID (path under knowledge/ without .md)."""
    k_dir = _get_knowledge_dir()
    # Guard against path traversal
    safe_path = (k_dir / f"{concept_id}.md").resolve()
    if not str(safe_path).startswith(str(k_dir.resolve())):
        return {"error": "Path traversal prohibited"}
    if not safe_path.exists():
        return {"error": f"Concept '{concept_id}' not found."}

    parsed = _parse_markdown_file(safe_path)
    fm = parsed.get("frontmatter", {})
    source = fm.get("source", "Altostrat Singapore Employee Policy Handbook")
    title = fm.get("title", safe_path.stem)

    return {
        "id": concept_id,
        "title": title,
        "resource": source,
        "content": parsed.get("body", ""),
    }


def search_policy_docs(query: str) -> Dict[str, Any]:
    """Search the policy handbook using keyword & semantic token matching.
    Enforces Grounding Gate: returns found=False if confidence < 0.65 or topic is absent.
    """
    if not query or not query.strip():
        return {"found": False, "reason": "Empty query"}

    k_dir = _get_knowledge_dir()
    if not k_dir.exists():
        return {"found": False, "reason": "Knowledge directory not initialized"}

    query_tokens = set(re.findall(r'\w+', query.lower()))
    best_match = None
    best_score = 0.0

    for p in k_dir.rglob("*.md"):
        if p.name in ("index.md", "log.md"):
            continue
        parsed = _parse_markdown_file(p)
        body = parsed.get("body", "").lower()
        title = parsed.get("frontmatter", {}).get("title", "").lower()
        desc = parsed.get("frontmatter", {}).get("description", "").lower()

        text_to_match = f"{title} {desc} {body}"
        token_hits = sum(1 for t in query_tokens if t in text_to_match)
        if not token_hits:
            continue

        score = token_hits / len(query_tokens)
        # Boost if title contains query terms
        if any(t in title for t in query_tokens):
            score += 0.2

        if score > best_score:
            best_score = score
            fm = parsed.get("frontmatter", {})
            best_match = {
                "id": str(p.relative_to(k_dir)).removesuffix(".md"),
                "title": fm.get("title", p.stem),
                "source": fm.get("source", "Altostrat Singapore Employee Policy Handbook"),
                "content": parsed.get("body", "")[:1800],
                "score": round(min(score, 1.0), 2),
            }

    if not best_match or best_match["score"] < SIMILARITY_THRESHOLD:
        return {
            "found": False,
            "confidence": best_score,
            "message": "I looked through the Altostrat Singapore Employee Policy Handbook, but there is no policy on file regarding this topic. Please contact your HR Business Partner.",
        }

    return {
        "found": True,
        "confidence": best_match["score"],
        "concept_id": best_match["id"],
        "title": best_match["title"],
        "citation": f"[{best_match['title']} - Section Reference]",
        "source": best_match["source"],
        "content": best_match["content"],
    }
