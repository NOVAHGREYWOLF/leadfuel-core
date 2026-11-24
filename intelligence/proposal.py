"""own-7: explain, undo, stop.

Every proposal shows its sources. A reversible action carries an undo. Only the
kinds listed in REVERSIBLE_KINDS are reversible; every other kind (a send, a
post, a payment, and any kind this module does not know) is treated as
irreversible and is labelled so before approval. It fails closed: a kind nobody
listed is never shown as "Can be undone".

An approved proposal runs at most once. A second approve() is refused, and an
irreversible action is marked done before it runs, so a failure part way through
cannot be retried into a second send or payment from the same proposal.

One stop control refuses every new step the local AI tries to take.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

# The closed list is the REVERSIBLE one. Anything not here is irreversible.
REVERSIBLE_KINDS = frozenset({"edit", "calendar-block", "draft"})


class StopRequested(RuntimeError):
    """Raised when work is attempted after the stop control was pressed."""


class AlreadyApproved(RuntimeError):
    """Raised when an approved proposal is approved again."""


class StopControl:
    """The owner's stop button.

    It refuses every NEW step (approve, undo) once pressed. It cannot interrupt
    an action that is already running: a send or payment in flight completes or
    fails on its own. Callers that run long actions should call check() between
    their own steps.
    """

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
    _running: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("a proposal must show its sources")
        if self.reversible:
            if self.undo is None:
                raise ValueError("a reversible action must carry an undo")
        elif self.undo is not None:
            raise ValueError(
                f"a {self.kind} is treated as irreversible; do not attach an undo "
                f"(reversible kinds: {', '.join(sorted(REVERSIBLE_KINDS))})")

    @property
    def reversible(self) -> bool:
        return self.kind in REVERSIBLE_KINDS

    def explain(self) -> str:
        lines = [self.title, f"Why: {self.reason}", "Sources:"]
        lines.extend(f"- {s}" for s in self.sources)
        lines.append("Can be undone." if self.reversible else
                     f"CANNOT BE UNDONE: a {self.kind} is final once approved.")
        return "\n".join(lines)

    def approve(self, stop: StopControl):
        stop.check()
        if self.done or self._running:
            raise AlreadyApproved(
                f"{self.title!r} was already approved; it will not run twice")
        self._running = True
        try:
            if not self.reversible:
                # Fail closed: once an irreversible action starts, this
                # proposal is spent, even if the action raises.
                self.done = True
            result = self.action()
            self.done = True
            return result
        finally:
            self._running = False

    def undo_it(self, stop: StopControl):
        stop.check()
        if not self.reversible:
            raise ValueError(f"a {self.kind} cannot be undone")
        if not self.done:
            raise ValueError("nothing to undo: the action has not run")
        result = self.undo()  # type: ignore[misc]
        self.done = False
        return result
