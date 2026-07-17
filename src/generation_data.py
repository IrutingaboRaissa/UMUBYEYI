"""Load genuine conversational supervision for Umubyeyi's response generator.

ESConv supplies multi-turn emotional-support responses. The AMOD-derived file
under data/intent/ is separate project data used only to train the bilingual
intent classifier (see train_topic_classifier.py); it is not generator
supervision. The reviewed postpartum collection remains retrieval evidence and
is not expanded into templated training conversations.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

ESCONV_COMMIT = "f262d062ad74cb39b17ea476facc81568ddcba24"
ESCONV_SHA256 = "aa0556c5b330562ba009c1cd5137486bfa2a7255f33225a6524cd58f7efdd9af"
ESCONV_URL = (
    "https://raw.githubusercontent.com/thu-coai/Emotional-Support-Conversation/"
    f"{ESCONV_COMMIT}/ESConv.json"
)


def _normalise(text: str) -> str:
    return " ".join(str(text).split()).strip()


def grouped_split(group_id: str, seed: int = 42) -> str:
    """Deterministically assign a complete conversation/question to one split."""
    digest = hashlib.sha256(f"{seed}|{group_id}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 15:
        return "test"
    if bucket < 30:
        return "validation"
    return "train"


def format_generator_input(
    query: str, evidence: str = "", lang: str = "en", history: str = ""
) -> str:
    """Format training and runtime prompts without embedding a hard-coded answer."""
    language = "Kinyarwanda" if lang == "rw" else "English"
    evidence_text = _normalise(evidence) or "No external evidence supplied."
    history_text = _normalise(history)
    parts = [
        "Write an empathetic emotional-support response.",
        "Do not diagnose or invent medical facts.",
        f"Language: {language}",
        f"Evidence: {evidence_text}",
    ]
    if history_text:
        parts.append(f"Conversation: {history_text}")
    parts.extend([f"User: {_normalise(query)}", "Response:"])
    return "\n".join(parts)


def download_esconv(destination: Path) -> Path:
    """Download the pinned official ESConv file and verify its exact checksum."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        urllib.request.urlretrieve(ESCONV_URL, destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    if digest != ESCONV_SHA256:
        destination.unlink(missing_ok=True)
        raise ValueError(f"ESConv checksum mismatch: expected {ESCONV_SHA256}, got {digest}")
    return destination


def load_esconv(path: Path) -> list[dict]:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ESCONV_SHA256:
        raise ValueError(f"ESConv checksum mismatch: expected {ESCONV_SHA256}, got {digest}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows or "dialog" not in rows[0]:
        raise ValueError("Unexpected ESConv schema")
    return rows


def build_esconv_examples(
    conversations: Iterable[dict], max_supporter_turns: int = 6, seed: int = 42
) -> list[dict]:
    """Create response pairs while keeping every conversation in one split."""
    if max_supporter_turns < 1:
        raise ValueError("max_supporter_turns must be positive")
    examples: list[dict] = []
    for conversation_index, conversation in enumerate(conversations):
        conversation_id = f"esconv-{conversation_index:04d}"
        split = grouped_split(conversation_id, seed)
        situation = _normalise(conversation.get("situation", ""))
        history: list[str] = []
        supporter_count = 0
        for turn_index, turn in enumerate(conversation.get("dialog", [])):
            speaker = str(turn.get("speaker", "")).lower()
            content = _normalise(turn.get("content", ""))
            if not content:
                continue
            if speaker == "supporter" and history and supporter_count < max_supporter_turns:
                supporter_count += 1
                annotation = turn.get("annotation") or {}
                strategy = annotation.get("strategy") or "Other"
                recent_history = " ".join(history[-6:])
                latest_user = next(
                    (item.split(":", 1)[1].strip() for item in reversed(history)
                     if item.startswith("User:")),
                    situation,
                )
                examples.append({
                    "id": f"{conversation_id}-turn-{turn_index:02d}",
                    "group_id": conversation_id,
                    "dataset": "ESConv",
                    "split": split,
                    "language": "en",
                    "query": latest_user,
                    "history": recent_history,
                    "evidence": "",
                    "input": format_generator_input(latest_user, "", "en", recent_history),
                    "target": content,
                    "strategy": strategy,
                    "problem_type": conversation.get("problem_type", "unspecified"),
                    "source": "Liu et al. (2021), Emotional Support Conversation",
                    "source_url": "https://github.com/thu-coai/Emotional-Support-Conversation",
                })
            role = "Supporter" if speaker == "supporter" else "User"
            history.append(f"{role}: {content}")
    return examples


def dataset_summary(examples: list[dict]) -> dict:
    """Return auditable counts for a combined conversation dataset."""
    return {
        "examples": len(examples),
        "groups": len({row["group_id"] for row in examples}),
        "datasets": dict(Counter(row["dataset"] for row in examples)),
        "splits": dict(Counter(row["split"] for row in examples)),
        "languages": dict(Counter(row["language"] for row in examples)),
        "strategies": dict(Counter(row.get("strategy", "") for row in examples)),
        "groups_by_split": {
            split: len({row["group_id"] for row in examples if row["split"] == split})
            for split in ("train", "validation", "test")
        },
    }
