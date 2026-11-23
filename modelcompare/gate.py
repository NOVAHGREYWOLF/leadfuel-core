r"""mail2-38: the bridge methods the NovahOS chat page calls for a model comparison.

Shaped like home-node/app/assistant/chatgate.py: `build_gate(api, scripted)` returns a desk, and
every public `compare_*` method is served on the Api under the same name once the gate is listed in
assistant/gate_list.py (docs/NOVAHOS_MODEL_COMPARE.md says exactly how). Each method returns a
dict with an `ok` flag and never raises a refusal across the bridge.

READ EVERY METHOD AS "A PROMPT-INJECTED SCRIPT MAY CALL THIS" (api.py's own first line). What a
script can do with these: run local models, without tools or files, on text it supplies. The model
ids are checked against the local engine's own list, so no argument names a resource outside this
window. It cannot make anything leave the PC and it cannot write to a chat except by calling
`compare_pick` for a lane that finished, once.

NOTHING IS WRITTEN UNTIL THE OWNER PICKS. `compare_start` reads the chat's history and sends it
with the new message; it adds no row. `compare_pick` then writes the user message and the chosen
answer, in that order, exactly once. Discarding a comparison leaves the chat as it was.

The store this needs is `assistant.store.ConvStore` (checked against its source on 2026-11-23):
`get(conv_id)`, `history(conv_id)`, `new(title=None, model=None)`, `add_user(conv_id, text)`,
`start_assistant(conv_id, model)`, `finish_assistant(msg_id, text, *, tokens_in, tokens_out,
stop_reason)`.
"""
from __future__ import annotations

from typing import Callable

from .core import (LOCAL_ENGINES, MAX_MODELS, MIN_MODELS, Comparer, Refused)

# The scripted window (--selftest, --engine fake) registers a test double under this key, and the
# self-test needs something to compare. It is allowed ONLY when `scripted` is true.
_SCRIPTED_ENGINES = frozenset({"fake"})

NO_SUCH_CONVERSATION = "no_such_conversation"
RETRY_SAME_ANSWER = "retry_same_answer"


class CompareDesk:
    def __init__(self, comparer: Comparer, store, *,
                 context_fn: Callable[[str, list], list] | None = None) -> None:
        self.comparer = comparer
        self.store = store
        self._context_fn = context_fn

    # ---- what can be chosen ------------------------------------------------------------------------

    def compare_models(self) -> dict:
        return {"ok": True, "items": self.comparer.models(), "min": MIN_MODELS,
                "max": self.comparer.max_models, "sequential": True, "local_only": True,
                "busy": self.comparer.busy()}

    # ---- a run --------------------------------------------------------------------------------------

    def compare_start(self, text: str, models=None, conv_id: str | None = None) -> dict:
        text = str(text or "").strip()
        conv_id = str(conv_id) if conv_id else ""
        if isinstance(models, (str, bytes)):   # one name, not a list of characters
            models = [models.decode("utf-8", "replace") if isinstance(models, bytes) else models]
        try:
            if conv_id and self.store.get(conv_id) is None:
                return {"ok": False, "refused": NO_SUCH_CONVERSATION, "error": "no such conversation"}
            # start() validates everything before it runs or writes anything, so a refusal here has
            # cost one read of the history and nothing else.
            run = self.comparer.start(self._messages(conv_id, text), models, conv_id=conv_id)
        except Refused as r:
            return _refused(r)
        out = run.snapshot(None)
        out["ok"] = True
        return out

    def compare_poll(self, run_id: str, since: int | None = None) -> dict:
        try:
            run = self.comparer.get(run_id)
        except Refused as r:
            return _refused(r)
        try:
            seen = None if since is None else int(since)
        except (TypeError, ValueError):
            seen = None                        # a version we cannot read: send everything, never less
        out = run.snapshot(seen)
        out["ok"] = True
        return out

    def compare_stop(self, run_id: str) -> dict:
        return self._control(self.comparer.stop, run_id)

    def compare_skip(self, run_id: str) -> dict:
        return self._control(self.comparer.skip, run_id)

    def _control(self, fn, run_id: str) -> dict:
        try:
            run = fn(run_id)
        except Refused as r:
            return _refused(r)
        out = run.snapshot(None)
        out["ok"] = True
        return out

    # ---- keeping an answer --------------------------------------------------------------------------

    def compare_pick(self, run_id: str, model: str) -> dict:
        """Write the message and the chosen answer into the chat, once."""
        try:
            run = self.comparer.get(run_id)
            model = str(model or "")
            if (run.picked is None and run.assistant_msg_id is not None
                    and run.assistant_model != model):
                # (Only while no answer is claimed: a kept answer says `already_picked`, below.)
                # An earlier try began the answer row for another model and then failed. That row's
                # model label cannot be changed from here, and writing this model's words under the
                # other model's name would be a false record. Same answer again, or discard.
                return {"ok": False, "refused": RETRY_SAME_ANSWER,
                        "error": "Saving %s failed part-way. Try that answer again, or discard this "
                                 "comparison." % run.assistant_model}
            lane = self.comparer.mark_picked(run, model)
        except Refused as r:
            return _refused(r)
        try:
            conv_id = run.conv_id or self.store.new(model=lane.model)["id"]
            run.conv_id = conv_id              # a retry after a failed write reuses this chat
            if not run.user_written:           # ...and does not write the question a second time
                self.store.add_user(conv_id, run.prompt)
                run.user_written = True
            if run.assistant_msg_id is None:   # a retry finishes the row it began, not a second one
                run.assistant_msg_id = self.store.start_assistant(conv_id, lane.model)
                run.assistant_model = lane.model
            msg_id = run.assistant_msg_id
            self.store.finish_assistant(msg_id, lane.text, tokens_in=lane.tokens_in,
                                        tokens_out=lane.tokens_out,
                                        stop_reason=lane.stop_reason or "end_turn")
        except Exception:
            # The claim was made before the write so a double click cannot write twice. A write
            # that failed gives the claim back, so the owner can try again, and the error is not
            # hidden: the Api's guard turns it into a visible message.
            self.comparer.unpick(run)
            raise
        return {"ok": True, "conv_id": conv_id, "msg_id": msg_id, "model": lane.model,
                "continue_with": lane.model}

    def compare_export(self, run_id: str) -> dict:
        try:
            run = self.comparer.get(run_id)
        except Refused as r:
            return _refused(r)
        return {"ok": True, "markdown": run.to_markdown()}

    # ---- not bridge methods: the Api calls these itself ----------------------------------------------

    def busy(self) -> str | None:
        """A sentence if a comparison is running. `Api._start_turn` asks this first, because an
        ordinary turn and a comparison would share one engine instance."""
        return self.comparer.busy()

    def shutdown(self) -> None:
        self.comparer.stop_all()

    # ---- the messages every lane gets --------------------------------------------------------------------

    def _messages(self, conv_id: str, text: str) -> list[dict]:
        history = list(self.store.history(conv_id)) if conv_id else []
        history.append({"role": "user", "content": text})
        if self._context_fn is not None:
            try:
                history = self._context_fn(conv_id, history) or history
            except Exception:  # noqa: BLE001 -- a broken prompt helper costs the prompt, not the run
                pass
        return history


def _refused(r: Refused) -> dict:
    return {"ok": False, "refused": r.code, "error": r.message}


def build_gate(api, scripted: bool) -> CompareDesk:
    engines = getattr(api, "engines", None)
    store = getattr(api, "store", None)
    if not isinstance(engines, dict) or store is None or not hasattr(store, "history"):
        raise RuntimeError("the compare gate needs the Api's engines and an assistant.store.ConvStore")

    def blocker() -> str | None:
        turn = getattr(api, "_turn", None)
        if turn is not None and not turn.done.is_set():
            return "A chat turn is running. Wait for it, or stop it, then compare."
        return None

    def lease(method: str) -> Callable[[str], None]:
        # The GPU lease broker (assistant/panesgate.py) is looked up at the moment a lane starts or
        # ends, not when the gate is built: gates are built in a list and `api.panes` may not exist
        # yet. A broker that is absent is simply not told (a normal turn does the same).
        def tell(token: str) -> None:
            fn = getattr(getattr(api, "panes", None), method, None)
            if callable(fn):
                fn(token)
        return tell

    context = getattr(api, "_chat_prompt_context", None)   # this chat's own system prompt
    allowed = LOCAL_ENGINES | (_SCRIPTED_ENGINES if scripted else frozenset())
    comparer = Comparer(engines, local_engines=allowed, blocker=blocker,
                        on_lane_start=lease("turn_started"), on_lane_end=lease("turn_finished"))
    return CompareDesk(comparer, store, context_fn=context if callable(context) else None)
