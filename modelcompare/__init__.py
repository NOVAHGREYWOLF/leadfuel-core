"""mail2-38: one prompt across several LOCAL models, answers side by side.

Scope and wiring: docs/NOVAHOS_MODEL_COMPARE.md. Picture: docs/mockups/model-compare.html.
Local engines only, one lane at a time, no tools, nothing written until the owner picks an answer.
"""
from .core import (
    ALREADY_PICKED, BUSY, CANCELLED, DONE, ERROR, INCOMPLETE, LOCAL_ENGINES, MAX_MODELS,
    MIN_MODELS, NOT_FINISHED, NOT_INSTALLED, NOT_LOCAL, NOT_PICKABLE, NOT_RUNNING, QUEUED,
    RUNNING, SKIPPED, CompareRun, Comparer, Lane, Refused, looks_remote,
)
from .gate import CompareDesk, build_gate

__all__ = [
    "ALREADY_PICKED", "BUSY", "CANCELLED", "DONE", "ERROR", "INCOMPLETE", "LOCAL_ENGINES",
    "MAX_MODELS", "MIN_MODELS", "NOT_FINISHED", "NOT_INSTALLED", "NOT_LOCAL", "NOT_PICKABLE",
    "NOT_RUNNING", "QUEUED", "RUNNING", "SKIPPED", "CompareDesk", "CompareRun", "Comparer",
    "Lane", "Refused", "build_gate", "looks_remote",
]
