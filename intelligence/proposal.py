"""own-7: explain, undo, stop.

Every proposal shows its sources. A reversible action carries an undo. A send, a
post or a payment is irreversible and is labelled so before approval. One stop
control halts everything the local AI is doing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

IRREVERSIBLE_KINDS = frozenset({"send", "post", "payment"})


class StopRequested(RuntimeError):
    """Raised when work is attempted after the stop control was pressed."""


class StopControl:
    def __init__(self) -> None:
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def resume(self) -> None:
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def check(self) -> None:
        if self._stopped:
            raise StopRequested("stopped by the owner")


@dataclass
class Proposal:
    title: str
    kind: str
    reason: str
    sources: list[str]
    action: Callable[[], object]
    undo: Optional[Callable[[], object]] = None
    done: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("a proposal must show its sources")
        if self.kind in IRREVERSIBLE_KINDS:
            if self.undo is not None:
                raise ValueError(f"a {self.kind} cannot be undone; do not attach an undo")
        elif self.undo is None:
            raise ValueError("a reversible action must carry an undo")

    @property
    def reversible(self) -> bool:
        return self.kind not in IRREVERSIBLE_KINDS

    def explain(self) -> str:
        lines = [self.title, f"Why: {self.reason}", "Sources:"]
        lines.extend(f"- {s}" for s in self.sources)
        lines.append("Can be undone." if self.reversible else
                     f"CANNOT BE UNDONE: a {self.kind} is final once approved.")
        return "\n".join(lines)

    def approve(self, stop: StopControl):
        stop.check()
        result = self.action()
        self.done = True
        return result

    def undo_it(self, stop: StopControl):
        stop.check()
        if not self.reversible:
            raise ValueError(f"a {self.kind} cannot be undone")
        if not self.done:
            raise ValueError("nothing to undo: the action has not run")
        result = self.undo()  # type: ignore[misc]
        self.done = False
        return result
