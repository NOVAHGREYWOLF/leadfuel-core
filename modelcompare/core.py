r"""mail2-38: one prompt, several LOCAL models, one after another, answers kept side by side.

This module is the fan-out. It owns no model, opens no socket and imports nothing that could: it
is handed the app's engines (the `lfdesk.engine` contract: `name`, `available()`, `models()`,
`stream(messages, *, model, tools, on_tool)`, `cancel()`) and drives them. Everything the owner
decided is a rule here, and each rule has a test that tries to break it:

  LOCAL ONLY, BY CONSTRUCTION. A model id is resolved only through an engine whose key AND `.name`
  are in `local_engines` (default {"local"}). Every other engine is never asked anything: not
  `models()`, not `available()`, not `stream()`. So a cloud model cannot be reached by naming it,
  and there is no fallback to add one: an unknown id is REFUSED, not routed. A cloud model in a
  fan-out is a later decision of the owner and would need the spend gate (it multiplies cost by the
  number of lanes); this file has no switch for it on purpose.

  ONE LANE AT A TIME. `lfdesk.engine.local.LocalEngine` holds one live response and one cancel flag
  per instance, and Ollama reloads a model on a swap (25 s measured, engine/README.md) while the
  card holds one model. Two lanes in parallel on one engine instance would clobber each other's
  cancel, and would not be faster. So lanes run in the order given, and the page says so.

  NO TOOLS, NO FILES. Each lane gets `tools=None, on_tool=None`. N models each running a tool is N
  times the side effects; a compare is for reading answers. A model that emits a tool call anyway
  is ignored and the lane carries a warning. The registry is never touched.

  A STATE IS NEVER GUESSED. A lane is `done` only if its stream said so. A stream that ends with no
  terminal chunk is `incomplete`, not `done`; an engine that raises is `error`; a stop is
  `cancelled` or `skipped`. A check that cannot establish a state must not report one.

  NOTHING IS WRITTEN HERE. The run lives in memory. The host (gate.py) writes a conversation row
  only when the owner picks an answer.

Law 9: this module imports no network, process or file-transfer library (tests/test_modelcompare.py
parses the source and fails if one appears, with a positive control proving the check can see).
"""
from __future__ import annotations

import itertools
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Iterable

# ---- the rules, as data -----------------------------------------------------------------------

LOCAL_ENGINES = frozenset({"local"})   # lfdesk.engine.local.LocalEngine.name. Nothing else, ever.
MIN_MODELS = 2
MAX_MODELS = 4
MAX_LANE_CHARS = 200_000               # bounds memory; a lane past this stops growing and says so
KEEP_RUNS = 8                          # finished runs held in memory, oldest dropped first
# Measured on this estate (home-node/app/lfdesk/policy.py MAX_PARAMS_B = 9.0, and the 14B run that
# spilled 6 GB out of VRAM and ran 5.5x slower, lfdesk/engine/README.md). Only a label.
SLOW_ABOVE_PARAMS_B = 9.0

# Lane states. TERMINAL ones never change again.
QUEUED, RUNNING = "queued", "running"
DONE, ERROR, CANCELLED, SKIPPED, INCOMPLETE = "done", "error", "cancelled", "skipped", "incomplete"
TERMINAL = frozenset({DONE, ERROR, CANCELLED, SKIPPED, INCOMPLETE})

# Run states.
RUN_RUNNING, RUN_FINISHED = "running", "finished"

# Refusal codes. The page shows `message`; code is for tests and for the page to branch on.
EMPTY_PROMPT = "empty_prompt"
TOO_FEW = "too_few_models"
TOO_MANY = "too_many_models"
NOT_LOCAL = "not_local"
NOT_INSTALLED = "not_installed"
NO_LOCAL_ENGINE = "no_local_engine"
BUSY = "busy"
NO_SUCH_RUN = "no_such_run"
NO_SUCH_LANE = "no_such_lane"
NOT_RUNNING = "not_running"
NOT_FINISHED = "not_finished"
NOT_PICKABLE = "not_pickable"
ALREADY_PICKED = "already_picked"

# Names that say "this is somebody else's server" even when the string reached us by a side door.
# This is the MESSAGE choice only. Enforcement is that an id must be in a local engine's own list.
_REMOTE_SUFFIXES = ("-cloud", ":cloud")
_REMOTE_PREFIXES = ("claude", "gpt-", "gpt4", "o1", "o3", "o4", "gemini", "grok", "anthropic/",
                    "openai/", "google/")


class Refused(Exception):
    """A request that was turned down BEFORE anything ran. Carries a code and a sentence."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def looks_remote(model_id: str) -> bool:
    n = str(model_id or "").strip().lower()
    return n.endswith(_REMOTE_SUFFIXES) or n.startswith(_REMOTE_PREFIXES)


def parse_params_b(text) -> float | None:
    """'7.6B' -> 7.6, '137M' -> 0.137, anything else -> None (unknown is not zero)."""
    s = str(text or "").strip().upper()
    if len(s) < 2 or s[-1] not in "BMK":
        return None
    try:
        n = float(s[:-1])
    except ValueError:
        return None
    return n * {"B": 1.0, "M": 1e-3, "K": 1e-6}[s[-1]]


# ---- one lane, one run ------------------------------------------------------------------------

@dataclass
class Lane:
    index: int
    model: str
    engine_name: str
    slow: bool = False
    state: str = QUEUED
    text: str = ""
    thinking: str = ""
    error: str = ""
    stop_reason: str = ""
    tokens_in: int | None = None
    tokens_out: int | None = None
    elapsed_ms: int | None = None
    first_token_ms: int | None = None
    warnings: list = field(default_factory=list)
    picked: bool = False
    # not serialised
    _engine: object = field(default=None, repr=False)
    _started: float = field(default=0.0, repr=False)
    _interrupt: str = field(default="", repr=False)      # "", "skip" or "stop": WHY we cancelled it
    _text_capped: bool = field(default=False, repr=False)

    def warn(self, code: str, message: str) -> None:
        if not any(w["code"] == code for w in self.warnings):
            self.warnings.append({"code": code, "message": message})

    def to_dict(self) -> dict:
        return {
            "index": self.index, "model": self.model, "engine": self.engine_name,
            "slow": self.slow, "state": self.state, "text": self.text, "thinking": self.thinking,
            "error": self.error, "stop_reason": self.stop_reason,
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "elapsed_ms": self.elapsed_ms, "first_token_ms": self.first_token_ms,
            "warnings": [dict(w) for w in self.warnings], "picked": self.picked,
        }


class CompareRun:
    """One prompt, N lanes. Thread-safe: the worker writes, the page polls `snapshot()`."""

    def __init__(self, run_id: str, conv_id: str, messages: list[dict], lanes: list[Lane]) -> None:
        self.run_id = run_id
        self.conv_id = conv_id
        self.messages = [dict(m) for m in messages]
        self.prompt = _last_user_text(self.messages)
        self.lanes = lanes
        self.created = time.time()
        self.state = RUN_RUNNING
        self.stop_requested = False
        self.picked: str | None = None          # the model id whose answer was kept
        self.user_written = False               # the host has written the question to the chat
        self.assistant_msg_id: str | None = None   # ...and begun the answer row (retry-safe pick)
        self.version = 0
        self._lock = threading.RLock()          # guards lanes, state, version
        self._done = threading.Event()
        self._ilock = threading.Lock()          # guards _inflight, and ONLY that
        self._inflight: Lane | None = None      # the lane currently inside engine.stream()

    # -- state -------------------------------------------------------------------------------
    def _bump(self) -> None:
        self.version += 1

    @property
    def finished(self) -> bool:
        return self.state == RUN_FINISHED

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def lane(self, model: str) -> Lane | None:
        for ln in self.lanes:
            if ln.model == model:
                return ln
        return None

    def current_index(self) -> int | None:
        for ln in self.lanes:
            if ln.state == RUNNING:
                return ln.index
        return None

    # -- reading -----------------------------------------------------------------------------
    def snapshot(self, since: int | None = None) -> dict:
        """The whole run as of now. `since` is the version the page last saw: if nothing moved the
        answer is small and says `changed: False`, so a poll at rest costs almost nothing."""
        with self._lock:
            base = {"run_id": self.run_id, "conv_id": self.conv_id, "state": self.state,
                    "version": self.version, "picked": self.picked, "sequential": True,
                    "current": self.current_index(), "count": len(self.lanes)}
            if since is not None and since == self.version:
                base["changed"] = False
                return base
            base["changed"] = True
            base["prompt"] = self.prompt
            base["lanes"] = [ln.to_dict() for ln in self.lanes]
            return base

    def record(self) -> dict:
        """JSON-safe copy of the whole run, for a host that wants to persist it."""
        snap = self.snapshot(None)
        snap["created"] = self.created
        return snap

    def to_markdown(self) -> str:
        """Every answer, in lane order, as plain text to copy. Model text is data, not markup we
        interpret: it is written out as given under a heading we made."""
        with self._lock:
            out = ["# Model comparison", "", "Prompt:", "", _quote(self.prompt), ""]
            for ln in self.lanes:
                bits = [ln.state]
                if ln.elapsed_ms is not None:
                    bits.append("%.1f s" % (ln.elapsed_ms / 1000.0))
                if ln.tokens_out is not None:
                    bits.append("%d tokens" % ln.tokens_out)
                out += ["## %s (%s)" % (ln.model, ", ".join(bits)), ""]
                if ln.error:
                    out += ["Error: " + ln.error, ""]
                out += [ln.text.rstrip() or "(no answer)", ""]
            return "\n".join(out).rstrip() + "\n"


def _quote(text: str) -> str:
    return "\n".join("> " + line for line in str(text).splitlines()) or ">"


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content") or "")
    return ""


# ---- the desk ---------------------------------------------------------------------------------

class Comparer:
    """Holds the runs and starts them. One run at a time, estate-wide for this window.

    `blocker` is a host callable returning None, or a sentence saying why a comparison may not
    start right now (a chat turn is running; the GPU is leased to a render). It is asked once, at
    start. `on_lane_start` / `on_lane_end` take a token string, so the host's GPU lease broker can
    be told a local turn is on the card (the same tell `Api._lease_watch` gives for a normal turn);
    a hook that raises costs the hook, never the lane.
    """

    def __init__(self, engines: dict, *, local_engines: Iterable[str] = LOCAL_ENGINES,
                 blocker: Callable[[], str | None] | None = None,
                 on_lane_start: Callable[[str], None] | None = None,
                 on_lane_end: Callable[[str], None] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 max_models: int = MAX_MODELS, keep_runs: int = KEEP_RUNS) -> None:
        self._engines = dict(engines or {})
        self._allow = frozenset(local_engines)
        self._blocker = blocker
        self._on_start = on_lane_start
        self._on_end = on_lane_end
        self._clock = clock
        self._max = int(max_models)
        self._keep = int(keep_runs)
        self._lock = threading.RLock()
        self._runs: "OrderedDict[str, CompareRun]" = OrderedDict()
        self._active: CompareRun | None = None
        self._ids = itertools.count(1)

    @property
    def max_models(self) -> int:
        return self._max

    # -- which engines may be used ------------------------------------------------------------
    def _local(self) -> list[tuple[str, object]]:
        """The engines a lane may run on. A key in the allow-list is not enough: the object has to
        call itself local too, so a cloud engine filed under the key 'local' is still not used."""
        out = []
        for key, eng in self._engines.items():
            if key in self._allow and getattr(eng, "name", key) in self._allow:
                out.append((key, eng))
        return out

    # -- what can be chosen ---------------------------------------------------------------------
    def models(self) -> list[dict]:
        """One row per chat-capable local model, or one 'unavailable' row per local engine that
        cannot answer. Never touches a non-local engine."""
        rows: list[dict] = []
        for key, eng in self._local():
            ok, why = _available(eng)
            if not ok:
                rows.append({"engine": key, "id": "", "available": False, "reason": why})
                continue
            meta = _catalog(eng)
            for mid in _model_ids(eng):
                if looks_remote(mid):
                    continue
                row = {"engine": key, "id": mid, "available": True, "reason": "", "slow": False,
                       "params_b": None, "size_gb": None, "vision": False}
                info = meta.get(mid)
                if info:
                    pb = parse_params_b(info.get("parameter_size"))
                    row["params_b"] = pb
                    row["slow"] = bool(pb is not None and pb > SLOW_ABOVE_PARAMS_B)
                    size = info.get("size_bytes")
                    row["size_gb"] = round(size / 1e9, 2) if isinstance(size, (int, float)) and size else None
                    row["vision"] = bool(info.get("supports_vision"))
                rows.append(row)
        return rows

    # -- starting ---------------------------------------------------------------------------------
    def check(self, models, *, prompt: str = "x") -> list[tuple[str, object, str]]:
        """Everything `start` refuses on, without starting. Returns [(model, engine_key, engine)]
        in the order given, de-duplicated. Raises Refused. Writes nothing and runs nothing."""
        if not str(prompt or "").strip():
            raise Refused(EMPTY_PROMPT, "There is nothing to send: the message is empty.")
        wanted: list[str] = []
        for m in list(models or []):
            mid = str(m or "").strip()
            if mid and mid not in wanted:
                wanted.append(mid)
        for mid in wanted:
            if looks_remote(mid):
                raise Refused(NOT_LOCAL, "%s is not a model on this PC. Compare is local only; a "
                              "cloud model needs your decision first and is never a fallback." % mid)
        if len(wanted) < MIN_MODELS:
            raise Refused(TOO_FEW, "Choose at least %d different local models to compare." % MIN_MODELS)
        if len(wanted) > self._max:
            raise Refused(TOO_MANY, "Compare up to %d models at a time; %d were chosen. They run one "
                          "after another, so more only means a longer wait." % (self._max, len(wanted)))
        local = self._local()
        if not local:
            raise Refused(NO_LOCAL_ENGINE, "No local engine is set up, so there is nothing to compare.")
        listed: dict[str, tuple[str, object]] = {}
        for key, eng in local:
            ok, why = _available(eng)
            if not ok:
                continue
            for mid in _model_ids(eng):
                listed.setdefault(mid, (key, eng))
        plan = []
        for mid in wanted:
            hit = listed.get(mid)
            if hit is None:
                raise Refused(NOT_INSTALLED, "%s is not installed on this PC's local engine (or the "
                              "engine is not answering), so it was not run." % mid)
            plan.append((mid, hit[0], hit[1]))
        return plan

    def start(self, messages: list[dict], models, *, conv_id: str = "") -> CompareRun:
        """Validate everything, then start. All refusals happen before a thread exists."""
        msgs = [dict(m) for m in (messages or [])]
        prompt = _last_user_text(msgs)
        plan = self.check(models, prompt=prompt)
        why = None
        if self._blocker is not None:
            try:
                why = self._blocker()
            except Exception as exc:  # noqa: BLE001 -- a blocker that cannot answer must not say "free"
                why = "could not tell whether the GPU is free (%s: %s)" % (type(exc).__name__, exc)
        if why:
            raise Refused(BUSY, str(why))
        with self._lock:
            if self._active is not None and not self._active.finished:
                raise Refused(BUSY, "A comparison is already running. Stop it or wait for it to finish.")
            run_id = "cmp-%d" % next(self._ids)
            lanes = []
            for i, (mid, key, eng) in enumerate(plan):
                ln = Lane(index=i, model=mid, engine_name=key, _engine=eng)
                ln.slow = bool(_slow(eng, mid))
                lanes.append(ln)
            run = CompareRun(run_id, str(conv_id or ""), msgs, lanes)
            self._active = run
            self._runs[run_id] = run
            self._trim()
        try:
            threading.Thread(target=self._work, args=(run,), name="compare-" + run_id,
                             daemon=True).start()
        except Exception:
            with self._lock:
                self._active = None
                self._runs.pop(run_id, None)
            raise
        return run

    def _trim(self) -> None:
        # called with self._lock held
        for rid in list(self._runs):
            if len(self._runs) <= self._keep:
                break
            if self._runs[rid].finished and self._runs[rid] is not self._active:
                del self._runs[rid]

    # -- lookups and controls -----------------------------------------------------------------------
    def get(self, run_id: str) -> CompareRun:
        with self._lock:
            run = self._runs.get(str(run_id))
        if run is None:
            raise Refused(NO_SUCH_RUN, "That comparison is no longer held (only the last %d are kept)." % self._keep)
        return run

    def busy(self) -> str | None:
        """A sentence if a comparison is running, else None. The host asks this before it starts an
        ordinary turn, because both would use the same engine instance."""
        with self._lock:
            run = self._active
        if run is not None and not run.finished:
            return "A model comparison is running."
        return None

    def stop(self, run_id: str) -> CompareRun:
        """End the current lane and every lane that has not started. Finished lanes are kept."""
        run = self.get(run_id)
        with run._lock:
            if run.finished:
                raise Refused(NOT_RUNNING, "That comparison has already finished.")
            run.stop_requested = True
            for ln in run.lanes:
                if ln.state == QUEUED:
                    ln.state = CANCELLED
                    ln.stop_reason = "cancelled"
            run._bump()
        self._interrupt(run, "stop")
        return run

    def skip(self, run_id: str) -> CompareRun:
        """End only the lane that is running now; the next one starts."""
        run = self.get(run_id)
        if run.finished:
            raise Refused(NOT_RUNNING, "That comparison has already finished.")
        if not self._interrupt(run, "skip"):
            raise Refused(NOT_RUNNING, "No model is answering right now, so there is nothing to skip.")
        return run

    def _interrupt(self, run: CompareRun, kind: str) -> bool:
        """Ask the engine to stop the lane that is inside stream() right now, if there is one.

        The marker, and the call, are made under one lock, and the lane clears the marker under
        that same lock the moment it sees its terminal chunk. That is the whole point: LocalEngine's
        cancel flag is LEVEL-triggered ("applies to a turn that has not begun", engine/README.md),
        so a cancel that lands after the lane is over would still be waiting to cancel the owner's
        NEXT chat turn. We therefore never call engine.cancel() unless a lane is in flight, and the
        lane closes its generator after clearing the marker so the engine's own `finally` resets
        any cancel that arrived in the last instant. What is not closed: an engine that raises, in
        the same microseconds as a user stop. That window is noted in docs/NOVAHOS_MODEL_COMPARE.md.
        """
        with run._ilock:
            ln = run._inflight
            if ln is None:
                return False
            ln._interrupt = ln._interrupt or kind
            eng = ln._engine
            try:
                eng.cancel()
            except Exception:  # noqa: BLE001 -- a stop that raises is worse than one a frame late
                pass
            return True

    def stop_all(self) -> None:
        """Window closing: end whatever is running. Never raises."""
        with self._lock:
            run = self._active
        if run is not None and not run.finished:
            try:
                self.stop(run.run_id)
            except Refused:
                pass

    # -- the worker -----------------------------------------------------------------------------------
    def _work(self, run: CompareRun) -> None:
        try:
            for ln in run.lanes:
                with run._lock:
                    if run.stop_requested and ln.state == QUEUED:
                        ln.state = CANCELLED
                        ln.stop_reason = "cancelled"
                        run._bump()
                    if ln.state != QUEUED:
                        continue
                self._run_lane(run, ln)
        finally:
            with run._lock:
                for ln in run.lanes:           # a bug above must never leave a lane 'running'
                    if ln.state in (QUEUED, RUNNING):
                        ln.state = INCOMPLETE if ln.state == RUNNING else CANCELLED
                        ln.error = ln.error or "the comparison ended before this model finished"
                run.state = RUN_FINISHED
                run._bump()
            with self._lock:
                if self._active is run:
                    self._active = None
            run._done.set()

    def _hook(self, fn, token: str) -> None:
        if fn is None:
            return
        try:
            fn(token)
        except Exception:  # noqa: BLE001
            pass

    def _run_lane(self, run: CompareRun, ln: Lane) -> None:
        token = "%s-%d" % (run.run_id, ln.index)
        with run._lock:
            ln.state = RUNNING
            ln._started = self._clock()
            run._bump()
        self._hook(self._on_start, token)
        terminal = None            # the terminal chunk's kind: "done" or "error"
        meta: dict = {}
        err_text = ""
        raised = ""
        gen = None
        try:
            with run._ilock:
                # A stop that landed after this lane was picked but before it was marked in flight
                # found nothing to interrupt. `stop` sets the flag and THEN takes this lock to look
                # for a lane in flight; this block reads the flag and marks the lane in flight under
                # that same lock. So one of the two always sees the other: either the flag is seen
                # here (the engine is never asked at all) or the marker is seen there.
                stopped_early = run.stop_requested
                if stopped_early:
                    ln._interrupt = "stop"
                else:
                    run._inflight = ln
            if not stopped_early:
                gen = ln._engine.stream([dict(m) for m in run.messages], model=ln.model,
                                        tools=None, on_tool=None)
            for chunk in (gen if gen is not None else ()):
                kind = getattr(chunk, "kind", "")
                if kind in ("done", "error"):
                    terminal = kind
                    meta = dict(getattr(chunk, "meta", None) or {})
                    err_text = str(getattr(chunk, "text", "") or "")
                    break
                self._apply(run, ln, chunk, kind)
        except Exception as exc:  # noqa: BLE001 -- an engine crash is one lane's error, not the run's
            raised = "%s: %s" % (type(exc).__name__, str(exc)[:400])
        finally:
            with run._ilock:
                run._inflight = None
            if gen is not None:
                try:
                    gen.close()
                except Exception:  # noqa: BLE001
                    pass
            self._hook(self._on_end, token)
        self._settle(run, ln, terminal, meta, err_text, raised)

    def _apply(self, run: CompareRun, ln: Lane, chunk, kind: str) -> None:
        with run._lock:
            if kind == "text":
                delta = str(getattr(chunk, "text", "") or "")
                if not delta:
                    return
                channel = (getattr(chunk, "meta", None) or {}).get("channel")
                if channel == "thinking":
                    if len(ln.thinking) < MAX_LANE_CHARS:
                        ln.thinking += delta
                        run._bump()
                    return
                if ln.first_token_ms is None:
                    ln.first_token_ms = int((self._clock() - ln._started) * 1000)
                if len(ln.text) + len(delta) > MAX_LANE_CHARS:
                    if not ln._text_capped:
                        ln._text_capped = True
                        ln.warn("TEXT_CAPPED", "This answer is longer than %d characters; the rest is not kept."
                                % MAX_LANE_CHARS)
                    ln.text += delta[: max(0, MAX_LANE_CHARS - len(ln.text))]
                else:
                    ln.text += delta
                run._bump()
            elif kind in ("tool_use", "tool_result"):
                # tools=None, so this is an engine misbehaving. We never run it and never hide it.
                ln.warn("UNEXPECTED_TOOL_USE", "The model asked for a tool; none are offered in a "
                        "comparison, so it was ignored.")
                run._bump()
            elif kind == "thinking":
                delta = str(getattr(chunk, "text", "") or "")
                if delta and len(ln.thinking) < MAX_LANE_CHARS:
                    ln.thinking += delta
                    run._bump()
            else:
                ln.warn("UNKNOWN_CHUNK", "The engine sent a kind of message this view does not know: %r." % kind)
                run._bump()

    def _settle(self, run: CompareRun, ln: Lane, terminal, meta: dict, err_text: str, raised: str) -> None:
        with run._lock:
            ln.elapsed_ms = int((self._clock() - ln._started) * 1000)
            for w in meta.get("warnings") or []:
                if isinstance(w, dict) and w.get("code"):
                    ln.warn(str(w.get("code")), str(w.get("message") or w.get("code")))
            ti, to = meta.get("tokens_in"), meta.get("tokens_out")
            ln.tokens_in = ti if isinstance(ti, int) else None
            ln.tokens_out = to if isinstance(to, int) else None
            stopped = SKIPPED if ln._interrupt == "skip" else CANCELLED
            if raised:
                ln.state, ln.error = (stopped, "") if ln._interrupt else (ERROR, raised)
            elif terminal == "done":
                ln.stop_reason = str(meta.get("stop_reason") or "end_turn")
                if ln.stop_reason == "cancelled":
                    ln.state = stopped
                    if not ln._interrupt:
                        # The engine ended it itself (for example the owner declined the GPU question).
                        ln.error = "the engine stopped this model before it answered"
                else:
                    ln.state = DONE
                    if not ln.text.strip():
                        ln.warn("EMPTY_ANSWER", "The model finished without writing an answer.")
            elif terminal == "error":
                if ln._interrupt:
                    ln.state = stopped
                else:
                    ln.state, ln.error = ERROR, (err_text or "the engine reported an error")
            else:
                if ln._interrupt:
                    ln.state = stopped
                else:
                    ln.state = INCOMPLETE
                    ln.error = "the engine ended the stream without saying whether it finished"
            run._bump()

    # -- keeping an answer -------------------------------------------------------------------------------
    def mark_picked(self, run: CompareRun, model: str) -> Lane:
        """Claim the pick, once. Raises Refused unless the run is over and that lane is `done`.
        The host writes the conversation AFTER this returns, and calls `unpick` if the write fails."""
        with run._lock:
            if not run.finished:
                raise Refused(NOT_FINISHED, "Wait for the comparison to finish, or stop it, before choosing an answer.")
            ln = run.lane(str(model))
            if ln is None:
                raise Refused(NO_SUCH_LANE, "%s was not part of that comparison." % model)
            if run.picked is not None:
                raise Refused(ALREADY_PICKED, "An answer from this comparison was already kept (%s)." % run.picked)
            if ln.state != DONE:
                raise Refused(NOT_PICKABLE, "%s did not finish its answer, so it cannot be kept." % model)
            run.picked = ln.model
            ln.picked = True
            run._bump()
            return ln

    def unpick(self, run: CompareRun) -> None:
        with run._lock:
            if run.picked is not None:
                ln = run.lane(run.picked)
                if ln is not None:
                    ln.picked = False
            run.picked = None
            run._bump()


# ---- small, defensive probes of an engine -----------------------------------------------------------

def _available(eng) -> tuple[bool, str]:
    try:
        ok, why = eng.available()
        return bool(ok), str(why or "")
    except Exception as exc:  # noqa: BLE001
        return False, "%s: %s" % (type(exc).__name__, exc)


def _model_ids(eng) -> list[str]:
    try:
        return [str(m) for m in (eng.models() or []) if str(m)]
    except Exception:  # noqa: BLE001
        return []


def _catalog(eng) -> dict:
    """{model id: row} from the engine's optional `catalog()` (LocalEngine has one). Absent or
    failing means no size hints, never an error."""
    fn = getattr(eng, "catalog", None)
    if not callable(fn):
        return {}
    try:
        return {str(r.get("id")): r for r in (fn() or []) if isinstance(r, dict) and r.get("id")}
    except Exception:  # noqa: BLE001
        return {}


def _slow(eng, model_id: str) -> bool:
    info = _catalog(eng).get(model_id)
    pb = parse_params_b((info or {}).get("parameter_size"))
    return bool(pb is not None and pb > SLOW_ABOVE_PARAMS_B)
