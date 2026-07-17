"""Reproducible latency benchmark for core Umubyeyi runtime paths."""
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("UMU_DISABLE_OLLAMA", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag import UmubyeyiRAG
from screening import ScreeningService

OUTPUT = ROOT / "reports" / "performance" / "local_benchmark.json"


def checkin_answers():
    from screening import FEATURES
    values = {name: "No" for name in FEATURES}
    values.update({
        "Age": 27, "Relationship with husband": "Good",
        "Relationship with the newborn": "Good", "Feeling about motherhood": "Positive",
        "Recieved Support": "High", "Need for Support": "Low",
        "Trust and share feelings": "Yes", "Relax/sleep when newborn is tended ": "Yes",
        "Relax/sleep when the newborn is asleep": "Yes",
        "Feeling for regular activities": "Nothing (no difficulty)",
        "Depression before pregnancy (PHQ2)": "Negative",
        "Depression during pregnancy (PHQ2)": "Negative",
    })
    return values


def measure(action, repeats=100):
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    return {
        "repeats": repeats,
        "mean_ms": round(statistics.mean(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(ordered[max(0, int(.95 * len(ordered)) - 1)], 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def main():
    rag = UmubyeyiRAG()
    screening = ScreeningService()
    # Warm model/vectorizer paths before measuring steady-state application latency.
    screening.predict(checkin_answers())
    rag.answer("hello", force_lang="en")
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(), "python": platform.python_version(),
            "processor": platform.processor() or "not reported",
            "logical_cpu_count": os.cpu_count(),
            "ollama_disabled": os.environ.get("UMU_DISABLE_OLLAMA") == "1",
        },
        "benchmarks": {
            "safety_crisis": measure(lambda: rag.answer("I want to end my life", force_lang="en")),
            "greeting": measure(lambda: rag.answer("hello", force_lang="en")),
            "english_retrieval": measure(lambda: rag.answer(
                "I feel exhausted and cannot sleep after giving birth", force_lang="en")),
            "kinyarwanda_retrieval": measure(lambda: rag.answer(
                "Sinshobora gusinzira kandi ndananiwe", force_lang="rw")),
            "guided_checkin": measure(lambda: screening.predict(checkin_answers())),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
