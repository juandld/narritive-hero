"""
Lightweight categorization helpers used to assign domains/programs to notes.

The heuristics here are intentionally simple so they can be exercised in tests
without depending on external LLMs. Higher-fidelity classification can hook
into providers later while keeping the public API stable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


DOMAIN_KEYWORDS: Dict[str, Sequence[str]] = {
    "programming": (
        "code",
        "deploy",
        "api",
        "bug",
        "refactor",
        "commit",
        "backend",
        "frontend",
        "script",
        "library",
        "framework",
        "svelte",
        "python",
        "fastapi",
    ),
    "operations": (
        "schedule",
        "budget",
        "process",
        "handoff",
        "meeting",
        "supplier",
        "logistics",
        "ops",
        "vendor",
    ),
    "personal": (
        "journal",
        "health",
        "family",
        "travel",
        "weekend",
    ),
}


@dataclass
class CategorizationResult:
    domain: str
    confidence: float
    rationale: str
    program: Optional[str] = None
    program_confidence: Optional[float] = None
    program_rationale: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "domain": self.domain,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "program": self.program,
            "program_confidence": self.program_confidence,
            "program_rationale": self.program_rationale,
        }


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())


def _score_keywords(tokens: Sequence[str], keywords: Sequence[str]) -> Tuple[int, List[str]]:
    tokens_set = set(tokens)
    matched = [kw for kw in keywords if kw in tokens_set]
    return len(matched), matched


def _program_keywords(program: Dict[str, object]) -> Sequence[str]:
    raw_keywords = program.get("keywords") or []
    if isinstance(raw_keywords, str):
        raw_keywords = [part.strip() for part in raw_keywords.split(",") if part.strip()]
    if isinstance(raw_keywords, Sequence):
        keywords = [str(k).strip().lower() for k in raw_keywords if isinstance(k, (str, int))]
    else:
        keywords = []
    if not keywords:
        desc = str(program.get("description") or "").lower()
        keywords = [w for w in re.findall(r"[a-zA-Z0-9_]+", desc) if len(w) > 3][:8]
    return keywords


def categorize_note(transcription: str, title: Optional[str], programs: Sequence[Dict[str, object]]) -> CategorizationResult:
    tokens = _tokenize(f"{title or ''} {transcription or ''}")
    if not tokens:
        return CategorizationResult(
            domain="general",
            confidence=0.0,
            rationale="No textual content to analyze.",
        )

    best_domain = "general"
    best_conf = 0.0
    best_matched: List[str] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score, matched = _score_keywords(tokens, keywords)
        if score == 0:
            continue
        confidence = min(1.0, score / max(3, len(keywords) / 2))
        if confidence > best_conf:
            best_domain = domain
            best_conf = confidence
            best_matched = matched
    if best_conf == 0.0:
        rationale = "Defaulted to general domain (no keyword matches)."
        result = CategorizationResult(domain="general", confidence=0.1, rationale=rationale)
    else:
        rationale = f"Matched domain '{best_domain}' via keywords: {', '.join(best_matched)}."
        result = CategorizationResult(domain=best_domain, confidence=round(best_conf, 2), rationale=rationale)

    candidate_programs = [p for p in programs if isinstance(p, dict)]
    if result.domain != "general":
        candidate_programs = [
            p for p in candidate_programs if str(p.get("domain") or "").lower() == result.domain
        ] or candidate_programs

    best_program_key: Optional[str] = None
    best_program_score = 0
    best_program_keywords: List[str] = []
    for program in candidate_programs:
        key = str(program.get("key") or "").strip()
        if not key:
            continue
        program_keywords = _program_keywords(program)
        score, matched = _score_keywords(tokens, program_keywords)
        if score > best_program_score:
            best_program_score = score
            best_program_key = key
            best_program_keywords = matched

    if best_program_key:
        program_conf = min(1.0, best_program_score / 3) if best_program_score else 0.2
        result.program = best_program_key
        result.program_confidence = round(program_conf, 2)
        if best_program_keywords:
            result.program_rationale = f"Matched program keywords: {', '.join(best_program_keywords)}."
        else:
            result.program_rationale = "Chosen as highest-scoring program for domain."

    return result
