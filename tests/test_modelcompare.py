"""SURFACE mail2-38: one prompt across several LOCAL models. Every rule the owner set has a test that
tries to break it, against a FakeEngine that mirrors the `lfdesk.engine` contract.

What is NOT tested here, and must not be read as tested: the real `LocalEngine` (no model is run,
nothing is read from Ollama), the real `assistant.store.ConvStore` (a FakeStore with the same method
signatures stands in), and the page. The package has never been imported inside the real window.

A test that cannot see its subject must say so: every "never called" assertion below has a positive
control proving the counter moves when the thing IS called, and the two source scans have a fixture
that must be flagged.
"""
from __future__ import annotations

import ast
import copy
import glob
import itertools
import json
import os
import re
import threading
import time
import types
from dataclasses import dataclass

import pytest

import modelcompare
from modelcompare import core
from modelcompare.core import CompareRun, Comparer, Lane, Refused, looks_remote, parse_params_b
from modelcompare.gate import CompareDesk, RETRY_SAME_ANSWER, build_gate

WAIT = 5.0     # every wait is bounded, so a failing test cannot hang the suite
MSG = [{"role": "user", "content": "hello"}]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---- the test double ---------------------------------------------------------------------------------

@dataclass
class Chunk:
    kind: str
    text: str = ""
    tool_name: str = ""
    tool_input: dict | None = None
    is_error: bool = False
    meta: dict | None = None


class FakeEngine:
    """The `lfdesk.engine` contract, with LocalEngine's cancel semantics: `cancel()` sets a LEVEL
    flag, `stream` honours it at the start and clears it on the way out (in `finally`).

    A script is a list of steps per model:
      ("text", s)  ("think", s) thinking channel  ("think_kind", s) kind "thinking"
      ("tool",) ("tool_result",) ("mystery",)  ("mutate",) scribble on the messages it was given
      ("done", meta) ("error", s) ("raise", s)  ("hold",) wait for release[model] or a cancel
    """

    def __init__(self, name="local", scripts=None, models=None, catalog=None, ok=True, why="",
                 raises=()):
        self.name = name
        self.scripts = dict(scripts or {})
        self._models = list(models) if models is not None else list(self.scripts)
        self._ok, self._why, self._raises = ok, why, tuple(raises)
        self._glock = threading.Lock()
        self.calls = {"available": 0, "models": 0, "catalog": 0, "stream": 0, "cancel": 0}
        self.streamed = []          # model ids, in the order the stream bodies began
        self.seen = []              # one record per stream() call
        self.active = 0
        self.max_active = 0
        self.cancel_flag = False
        self.started = {m: threading.Event() for m in self.scripts}   # set when a lane is holding
        self.release = {m: threading.Event() for m in self.scripts}
        if catalog is not None:
            def _catalog():
                self.calls["catalog"] += 1
                if "catalog" in self._raises:
                    raise RuntimeError("catalog down")
                return list(catalog)
            self.catalog = _catalog          # optional on the contract: present only when asked for

    def available(self):
        self.calls["available"] += 1
        if "available" in self._raises:
            raise RuntimeError("probe down")
        return self._ok, self._why

    def models(self):
        self.calls["models"] += 1
        if "models" in self._raises:
            raise RuntimeError("list down")
        return list(self._models)

    def cancel(self):
        self.calls["cancel"] += 1
        self.cancel_flag = True

    def stream(self, messages, *, model, tools, on_tool):
        with self._glock:
            self.calls["stream"] += 1
            self.seen.append({"model": model, "messages": copy.deepcopy(messages), "tools": tools,
                              "on_tool": on_tool})
        return self._run(messages, model)

    def _run(self, messages, model):
        with self._glock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.streamed.append(model)
        try:
            if self.cancel_flag:                       # a cancel that landed before the turn began
                yield Chunk("done", meta={"stop_reason": "cancelled"})
                return
            for step in self.scripts[model]:
                op = step[0]
                if op == "text":
                    yield Chunk("text", step[1])
                elif op == "think":
                    yield Chunk("text", step[1], meta={"channel": "thinking"})
                elif op == "think_kind":
                    yield Chunk("thinking", step[1])
                elif op == "tool":
                    yield Chunk("tool_use", tool_name="delete_everything", tool_input={})
                elif op == "tool_result":
                    yield Chunk("tool_result", tool_name="delete_everything")
                elif op == "mystery":
                    yield Chunk("mystery")
                elif op == "mutate":
                    messages[0]["content"] = "TAMPERED"
                    messages.append({"role": "user", "content": "extra"})
                elif op == "done":
                    yield Chunk("done", meta=dict(step[1]) if len(step) > 1 else {})
                    return
                elif op == "error":
                    yield Chunk("error", step[1], is_error=True)
                    return
                elif op == "raise":
                    raise RuntimeError(step[1])
                elif op == "hold":
                    self.started[model].set()
                    deadline = time.monotonic() + WAIT
                    while not self.release[model].is_set():
                        if self.cancel_flag:
                            yield Chunk("done", meta={"stop_reason": "cancelled"})
                            return
                        if time.monotonic() > deadline:
                            raise TimeoutError("a test held a lane and never released it")
                        time.sleep(0.002)
                else:                                   # pragma: no cover - a typo in a test
                    raise AssertionError("unknown step %r" % (step,))
        finally:
            self.cancel_flag = False                   # LocalEngine clears its flag on the way out
            with self._glock:
                self.active -= 1


def say(text, **meta):
    return [("text", text), ("done", {"tokens_in": 3, "tokens_out": 5, **meta})]


def three():
    return FakeEngine(scripts={m: say(m.upper()) for m in "abc"})


@pytest.fixture
def mk():
    """Comparer factory. Teardown releases every held lane and stops the run, so no test leaves a
    thread waiting."""
    made = []

    def factory(engines, **kw):
        comparer = Comparer(engines, **kw)
        made.append((comparer, engines))
        return comparer

    yield factory
    for comparer, engines in made:
        for eng in engines.values():
            for ev in getattr(eng, "release", {}).values():
                ev.set()
        comparer.stop_all()
        run = comparer._active
        if run is not None:
            run.wait(WAIT)


def finish(run):
    assert run.wait(WAIT), "the comparison did not finish in %s s" % WAIT
    return run


def by_model(run):
    return {ln.model: ln for ln in run.lanes}


def states(run):
    return [ln.state for ln in run.lanes]


# ---- the rules in core.py ----------------------------------------------------------------------------

def test_lanes_run_in_order_one_at_a_time_with_no_tools(mk):
    eng = three()
    run = finish(mk({"local": eng}).start(MSG, ["a", "b", "c"]))
    assert states(run) == [core.DONE] * 3
    assert eng.streamed == ["a", "b", "c"]
    assert eng.max_active == 1                       # never two lanes inside the engine at once
    assert [r["model"] for r in eng.seen] == ["a", "b", "c"]
    assert all(r["tools"] is None and r["on_tool"] is None for r in eng.seen)
    assert [ln.text for ln in run.lanes] == ["A", "B", "C"]
    assert [(ln.tokens_in, ln.tokens_out) for ln in run.lanes] == [(3, 5)] * 3
    assert all(ln.stop_reason == "end_turn" for ln in run.lanes)
    assert run.state == core.RUN_FINISHED and run.current_index() is None


def test_lanes_cannot_alter_each_others_messages(mk):
    eng = FakeEngine(scripts={"a": [("mutate",), ("text", "A"), ("done", {})], "b": say("B")})
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    assert states(run) == [core.DONE, core.DONE]
    assert eng.seen[1]["messages"] == MSG            # lane b was handed the original, not a's scribbles
    assert run.messages == MSG                       # and so is the run's own record
    assert MSG[0]["content"] == "hello"              # and so is the caller's list


def test_a_non_local_engine_is_never_asked_anything(mk):
    local = FakeEngine(scripts={"a": say("A"), "b": say("B")})
    cloud = FakeEngine(name="claude", scripts={"big-model": say("X"), "other": say("Y")})
    comparer = mk({"local": local, "claude": cloud})
    assert [r["id"] for r in comparer.models()] == ["a", "b"]
    for wanted in (["a", "big-model"], ["a", "claude-sonnet"], ["big-model", "other"]):
        with pytest.raises(Refused) as ei:
            comparer.start(MSG, wanted)
        assert ei.value.code in (core.NOT_INSTALLED, core.NOT_LOCAL)
    finish(comparer.start(MSG, ["a", "b"]))
    assert cloud.calls == {"available": 0, "models": 0, "catalog": 0, "stream": 0, "cancel": 0}
    assert local.calls["stream"] == 2
    # positive control: this counter does move when the engine IS called, so a zero above means "not called"
    cloud.models()
    cloud.available()
    assert cloud.calls["models"] == 1 and cloud.calls["available"] == 1


def test_a_cloud_engine_filed_under_the_local_key_is_not_used(mk):
    liar = FakeEngine(name="claude", scripts={"m1": say("1"), "m2": say("2")})
    comparer = mk({"local": liar})
    assert comparer.models() == []
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["m1", "m2"])
    assert ei.value.code == core.NO_LOCAL_ENGINE
    # and the other way round: the right name under the wrong key is not used either
    local = FakeEngine(name="local", scripts={"m1": say("1"), "m2": say("2")})
    comparer = mk({"claude": local})
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["m1", "m2"])
    assert ei.value.code == core.NO_LOCAL_ENGINE
    assert liar.calls["stream"] == 0 and local.calls["stream"] == 0
    assert liar.calls["models"] == 0 and liar.calls["available"] == 0


def test_a_cloud_looking_id_listed_by_a_local_engine_is_hidden_and_refused(mk):
    eng = FakeEngine(scripts={"m1": say("1"), "m2": say("2"), "x-cloud": say("c")})
    comparer = mk({"local": eng})
    assert [r["id"] for r in comparer.models()] == ["m1", "m2"]
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["m1", "x-cloud"])
    assert ei.value.code == core.NOT_LOCAL
    assert "x-cloud" in ei.value.message
    assert eng.streamed == []


@pytest.mark.parametrize("model_id,remote", [
    ("claude-sonnet", True), ("gpt-4o", True), ("gemini-2", True), ("openai/gpt", True),
    ("qwen3-coder:480b-cloud", True), ("big:cloud", True), (" GPT-4 ", True),
    ("qwen2.5:7b-instruct-q4_K_M", False), ("mistral:7b", False), ("qwen3-vl:8b", False),
    ("", False), (None, False),
])
def test_looks_remote(model_id, remote):
    assert looks_remote(model_id) is remote


def _cases():
    models3 = {m: say(m) for m in "abc"}
    return {
        "empty_prompt": (core.EMPTY_PROMPT, [{"role": "user", "content": "   "}], ["a", "b"],
                         lambda: {"local": FakeEngine(scripts=models3)}),
        "no_messages": (core.EMPTY_PROMPT, [], ["a", "b"], lambda: {"local": FakeEngine(scripts=models3)}),
        "one_model": (core.TOO_FEW, MSG, ["a"], lambda: {"local": FakeEngine(scripts=models3)}),
        "no_models": (core.TOO_FEW, MSG, [], lambda: {"local": FakeEngine(scripts=models3)}),
        "models_none": (core.TOO_FEW, MSG, None, lambda: {"local": FakeEngine(scripts=models3)}),
        "duplicates": (core.TOO_FEW, MSG, ["a", "a"], lambda: {"local": FakeEngine(scripts=models3)}),
        "five_models": (core.TOO_MANY, MSG, list("abcde"),
                        lambda: {"local": FakeEngine(scripts={m: say(m) for m in "abcde"})}),
        "unknown_model": (core.NOT_INSTALLED, MSG, ["a", "zzz"], lambda: {"local": FakeEngine(scripts=models3)}),
        "engine_not_answering": (core.NOT_INSTALLED, MSG, ["a", "b"],
                                 lambda: {"local": FakeEngine(scripts=models3, ok=False, why="Ollama is off")}),
        "engine_probe_raises": (core.NOT_INSTALLED, MSG, ["a", "b"],
                                lambda: {"local": FakeEngine(scripts=models3, raises=("available",))}),
        "engine_list_raises": (core.NOT_INSTALLED, MSG, ["a", "b"],
                               lambda: {"local": FakeEngine(scripts=models3, raises=("models",))}),
        "no_engines_at_all": (core.NO_LOCAL_ENGINE, MSG, ["a", "b"], lambda: {}),
        "only_a_cloud_engine": (core.NO_LOCAL_ENGINE, MSG, ["a", "b"],
                                lambda: {"claude": FakeEngine(name="claude", scripts=models3)}),
        "remote_id": (core.NOT_LOCAL, MSG, ["a", "claude-sonnet"], lambda: {"local": FakeEngine(scripts=models3)}),
    }


@pytest.mark.parametrize("case", sorted(_cases()))
def test_a_refusal_runs_nothing_and_leaves_no_active_run(mk, case):
    code, messages, models, make_engines = _cases()[case]
    engines = make_engines()
    comparer = mk(engines)
    with pytest.raises(Refused) as ei:
        comparer.start(messages, models)
    assert ei.value.code == code and ei.value.message
    assert comparer.busy() is None
    assert len(comparer._runs) == 0 and comparer._active is None
    assert all(e.calls["stream"] == 0 for e in engines.values())


def test_check_dedupes_and_keeps_the_order_given(mk):
    eng = three()
    plan = mk({"local": eng}).check(["c", "a", "c", " b ", ""], prompt="hi")
    assert [(m, key) for m, key, _ in plan] == [("c", "local"), ("a", "local"), ("b", "local")]
    assert eng.calls["stream"] == 0


def test_the_cap_follows_max_models(mk):
    eng = FakeEngine(scripts={m: say(m) for m in "abcde"})
    comparer = mk({"local": eng}, max_models=5)
    assert comparer.max_models == 5
    run = finish(comparer.start(MSG, list("abcde")))
    assert states(run) == [core.DONE] * 5


def test_a_second_start_while_one_runs_is_busy(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng})
    run = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    assert comparer.busy() == "A model comparison is running."
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["a", "b"])
    assert ei.value.code == core.BUSY
    assert eng.calls["stream"] == 1                    # the refused start ran nothing
    eng.release["a"].set()
    finish(run)
    assert comparer.busy() is None
    run2 = finish(comparer.start(MSG, ["a", "b"]))     # and the desk is free again afterwards
    assert run2.run_id != run.run_id and states(run2) == [core.DONE] * 2


def test_a_blocker_sentence_refuses_before_anything_runs(mk):
    eng = three()
    comparer = mk({"local": eng}, blocker=lambda: "The GPU is rendering a video.")
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["a", "b"])
    assert ei.value.code == core.BUSY and "rendering" in ei.value.message
    assert eng.calls["stream"] == 0 and comparer.busy() is None


def test_a_blocker_that_raises_means_busy_never_free(mk):
    eng = three()

    def probe():
        raise RuntimeError("probe died")

    comparer = mk({"local": eng}, blocker=probe)
    with pytest.raises(Refused) as ei:
        comparer.start(MSG, ["a", "b"])
    assert ei.value.code == core.BUSY
    assert "could not tell" in ei.value.message and "RuntimeError" in ei.value.message
    assert eng.calls["stream"] == 0


def test_a_blocker_that_says_none_lets_the_run_start(mk):
    eng = three()
    run = finish(mk({"local": eng}, blocker=lambda: None).start(MSG, ["a", "b"]))
    assert states(run) == [core.DONE, core.DONE]


def test_one_lane_failing_does_not_stop_the_others(mk):
    eng = FakeEngine(scripts={
        "a": [("text", "par"), ("error", "model crashed")],
        "b": [("raise", "kaboom")],
        "c": say("C"),
        "d": [("error", "")],
    })
    run = finish(mk({"local": eng}).start(MSG, list("abcd")))
    lanes = by_model(run)
    assert lanes["a"].state == core.ERROR and lanes["a"].error == "model crashed" and lanes["a"].text == "par"
    assert lanes["b"].state == core.ERROR and "RuntimeError: kaboom" in lanes["b"].error
    assert lanes["c"].state == core.DONE and lanes["c"].text == "C"
    assert lanes["d"].state == core.ERROR and lanes["d"].error == "the engine reported an error"
    assert eng.streamed == ["a", "b", "c", "d"] and run.state == core.RUN_FINISHED


def test_a_stream_with_no_terminal_chunk_is_incomplete_never_done(mk):
    eng = FakeEngine(scripts={"a": [("text", "half an ans")], "b": say("B")})
    comparer = mk({"local": eng})
    run = finish(comparer.start(MSG, ["a", "b"]))
    a, b = run.lanes
    assert a.state == core.INCOMPLETE and a.text == "half an ans"
    assert "without saying" in a.error
    assert b.state == core.DONE
    with pytest.raises(Refused) as ei:
        comparer.mark_picked(run, "a")
    assert ei.value.code == core.NOT_PICKABLE


def test_stop_cancels_the_current_lane_and_every_queued_one(mk):
    eng = FakeEngine(scripts={"a": [("text", "x"), ("hold",), ("done", {})], "b": say("B"), "c": say("C")})
    comparer = mk({"local": eng})
    run = comparer.start(MSG, ["a", "b", "c"])
    assert eng.started["a"].wait(WAIT)
    assert comparer.stop(run.run_id) is run
    finish(run)
    assert states(run) == [core.CANCELLED] * 3
    assert run.lanes[0].text == "x" and run.lanes[0].stop_reason == "cancelled"
    assert run.stop_requested is True
    assert eng.streamed == ["a"]                       # b and c never reached the engine
    assert eng.calls["cancel"] == 1
    assert eng.cancel_flag is False                    # nothing left waiting to cancel the owner's next turn
    assert comparer.busy() is None


def test_skip_ends_only_the_current_lane_and_the_next_one_answers(mk):
    eng = FakeEngine(scripts={"a": [("text", "x"), ("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng})
    run = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    comparer.skip(run.run_id)
    finish(run)
    a, b = run.lanes
    assert a.state == core.SKIPPED and a.text == "x"
    assert b.state == core.DONE and b.text == "B"      # the cancel did not leak into the next lane
    assert eng.calls["cancel"] == 1 and eng.cancel_flag is False
    assert eng.streamed == ["a", "b"]


@pytest.mark.parametrize("verb", ["stop", "skip"])
def test_stop_and_skip_after_the_run_finished_never_touch_the_engine(mk, verb):
    eng = three()
    comparer = mk({"local": eng})
    run = finish(comparer.start(MSG, ["a", "b"]))
    with pytest.raises(Refused) as ei:
        getattr(comparer, verb)(run.run_id)
    assert ei.value.code == core.NOT_RUNNING
    assert eng.calls["cancel"] == 0 and eng.cancel_flag is False
    assert run.stop_requested is False
    again = finish(comparer.start(MSG, ["a", "b"]))    # the next turn on this engine is not cancelled
    assert states(again) == [core.DONE, core.DONE]


def test_skip_with_no_lane_in_the_engine_right_now_is_refused(mk):
    eng = three()
    comparer = mk({"local": eng})
    lane = Lane(index=0, model="a", engine_name="local", _engine=eng)
    idle = CompareRun("cmp-x", "", MSG, [lane])         # running, but nothing is inside stream()
    comparer._runs["cmp-x"] = idle
    with pytest.raises(Refused) as ei:
        comparer.skip("cmp-x")
    assert ei.value.code == core.NOT_RUNNING and "nothing to skip" in ei.value.message
    assert eng.calls["cancel"] == 0


def test_a_stop_that_lands_before_the_lane_is_in_flight_never_calls_the_engine(mk):
    eng = three()
    comparer = mk({"local": eng})
    lane = Lane(index=0, model="a", engine_name="local", _engine=eng)
    run = CompareRun("cmp-x", "", MSG, [lane])
    run.stop_requested = True
    comparer._run_lane(run, lane)
    assert lane.state == core.CANCELLED
    assert eng.calls["stream"] == 0 and eng.calls["cancel"] == 0
    assert run._inflight is None


def test_stop_all_ends_a_running_comparison_and_is_quiet_when_there_is_none(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng})
    comparer.stop_all()                                # nothing running: no error
    run = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    comparer.stop_all()
    finish(run)
    assert states(run) == [core.CANCELLED, core.CANCELLED]
    comparer.stop_all()                                # already over: still no error
    with pytest.raises(Refused) as ei:
        comparer.stop("cmp-999")
    assert ei.value.code == core.NO_SUCH_RUN


def test_an_engine_that_ended_the_lane_by_itself_is_cancelled_with_a_reason(mk):
    eng = FakeEngine(scripts={"a": [("text", "p"), ("done", {"stop_reason": "cancelled"})], "b": say("B")})
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    a = run.lanes[0]
    assert a.state == core.CANCELLED and a.error == "the engine stopped this model before it answered"


def test_the_thinking_channel_is_kept_apart_from_the_answer(mk):
    eng = FakeEngine(scripts={
        "a": [("think", "hmm "), ("think", "more"), ("text", "answer"), ("done", {})],
        "b": [("think_kind", "pondering"), ("text", "ok"), ("done", {})],
    })
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    a, b = run.lanes
    assert a.thinking == "hmm more" and a.text == "answer"
    assert b.thinking == "pondering" and b.text == "ok"
    assert a.first_token_ms is not None               # first token is the first ANSWER token


def test_an_empty_answer_is_done_with_a_warning(mk):
    eng = FakeEngine(scripts={"a": [("done", {})], "b": say("B")})
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    a = run.lanes[0]
    assert a.state == core.DONE and a.text == ""
    assert [w["code"] for w in a.warnings] == ["EMPTY_ANSWER"]


def test_a_tool_chunk_is_ignored_and_flagged(mk):
    eng = FakeEngine(scripts={
        "a": [("tool",), ("tool_result",), ("text", "A"), ("done", {})],
        "b": [("mystery",), ("text", "B"), ("done", {})],
    })
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    a, b = run.lanes
    assert a.state == core.DONE and a.text == "A"
    assert [w["code"] for w in a.warnings] == ["UNEXPECTED_TOOL_USE"]    # once, not once per chunk
    assert [w["code"] for w in b.warnings] == ["UNKNOWN_CHUNK"] and b.text == "B"


def test_engine_warnings_ride_along_on_the_lane(mk):
    eng = FakeEngine(scripts={
        "a": [("text", "A"), ("done", {"warnings": [{"code": "NUM_CTX", "message": "trimmed"}, "junk", {}]})],
        "b": say("B"),
    })
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    assert run.lanes[0].warnings == [{"code": "NUM_CTX", "message": "trimmed"}]


def test_a_lane_stops_growing_past_the_cap_and_says_so(mk, monkeypatch):
    monkeypatch.setattr(core, "MAX_LANE_CHARS", 10)
    eng = FakeEngine(scripts={
        "a": [("text", "abcdefgh"), ("text", "ijklm"), ("text", "zzz"), ("think", "t" * 30),
              ("done", {})],
        "b": say("B"),
    })
    run = finish(mk({"local": eng}).start(MSG, ["a", "b"]))
    a = run.lanes[0]
    assert a.text == "abcdefghij" and a.state == core.DONE
    assert [w["code"] for w in a.warnings] == ["TEXT_CAPPED"]
    assert 0 < len(a.thinking) <= 30


def test_timing_is_measured_with_the_injected_clock_and_markdown_says_so(mk):
    tick = itertools.count()
    eng = FakeEngine(scripts={
        "a": [("text", "Hello"), ("done", {"tokens_in": 3, "tokens_out": 5})],
        "b": [("done", {})],
        "c": [("error", "boom")],
    })
    comparer = mk({"local": eng}, clock=lambda: float(next(tick)))
    run = finish(comparer.start(MSG, ["a", "b", "c"]))
    a, b, c = run.lanes
    assert (a.first_token_ms, a.elapsed_ms) == (1000, 2000)
    assert b.elapsed_ms == 1000 and b.first_token_ms is None and c.elapsed_ms == 1000
    md = run.to_markdown()
    assert md.startswith("# Model comparison\n\nPrompt:\n\n> hello\n")
    assert "## a (done, 2.0 s, 5 tokens)\n\nHello\n" in md
    assert "## b (done, 1.0 s)\n\n(no answer)\n" in md
    assert "## c (error, 1.0 s)\n\nError: boom\n\n(no answer)\n" in md
    assert md.endswith("\n") and not md.endswith("\n\n")


def test_snapshot_at_rest_is_small_and_says_nothing_changed(mk):
    run = finish(mk({"local": three()}).start(MSG, ["a", "b"]))
    full = run.snapshot()
    assert full["changed"] is True and len(full["lanes"]) == 2 and full["prompt"] == "hello"
    assert full["sequential"] is True and full["count"] == 2 and full["current"] is None
    quiet = run.snapshot(since=full["version"])
    assert quiet["changed"] is False and "lanes" not in quiet and "prompt" not in quiet
    assert quiet["state"] == core.RUN_FINISHED and quiet["version"] == full["version"]
    assert run.snapshot(since=full["version"] - 1)["changed"] is True
    assert run.snapshot(since=0)["changed"] is True


def test_the_version_moves_while_a_lane_streams(mk):
    eng = FakeEngine(scripts={"a": [("text", "x"), ("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng})
    run = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    mid = run.snapshot()
    assert mid["state"] == core.RUN_RUNNING and mid["current"] == 0
    assert [ln["state"] for ln in mid["lanes"]] == [core.RUNNING, core.QUEUED]
    assert mid["lanes"][0]["text"] == "x"
    eng.release["a"].set()
    finish(run)
    assert run.snapshot(since=mid["version"])["changed"] is True


def test_models_rows_carry_size_params_vision_and_the_slow_label(mk):
    catalog = [
        {"id": "m7", "parameter_size": "7.6B", "size_bytes": 4_700_000_000, "supports_vision": False},
        {"id": "m14", "parameter_size": "14.8B", "size_bytes": 9_000_000_000},
        {"id": "v8", "parameter_size": "8.8B", "size_bytes": 6_100_000_000, "supports_vision": True},
        {"id": "tiny", "parameter_size": "137M", "size_bytes": 0},
        {"id": "odd", "parameter_size": "lots", "size_bytes": "big"},
        {"not_an_id": True}, "not a row",
    ]
    eng = FakeEngine(models=["m7", "m14", "v8", "tiny", "odd", "unlisted"], catalog=catalog)
    rows = {r["id"]: r for r in mk({"local": eng}).models()}
    assert list(rows) == ["m7", "m14", "v8", "tiny", "odd", "unlisted"]
    assert rows["m7"]["size_gb"] == 4.7 and rows["m7"]["params_b"] == pytest.approx(7.6)
    assert rows["m7"]["slow"] is False and rows["m7"]["vision"] is False
    assert rows["m14"]["slow"] is True                 # 14.8B is past 9.0B: the card spills
    assert rows["v8"]["vision"] is True and rows["v8"]["slow"] is False
    assert rows["tiny"]["params_b"] == pytest.approx(0.137) and rows["tiny"]["size_gb"] is None
    assert rows["odd"]["params_b"] is None and rows["odd"]["slow"] is False and rows["odd"]["size_gb"] is None
    assert rows["unlisted"]["params_b"] is None and rows["unlisted"]["slow"] is False
    assert all(r["available"] is True and r["engine"] == "local" for r in rows.values())


def test_a_slow_model_is_labelled_on_its_lane(mk):
    eng = FakeEngine(scripts={"big": say("B"), "small": say("S")},
                     catalog=[{"id": "big", "parameter_size": "14.8B"}, {"id": "small", "parameter_size": "4B"}])
    run = finish(mk({"local": eng}).start(MSG, ["big", "small"]))
    assert [ln.slow for ln in run.lanes] == [True, False]


def test_an_engine_with_no_catalog_or_a_failing_one_gives_rows_without_hints(mk):
    plain = FakeEngine(models=["a", "b"])
    assert not hasattr(plain, "catalog")
    broken = FakeEngine(models=["a", "b"], catalog=[{"id": "a", "parameter_size": "20B"}], raises=("catalog",))
    for eng in (plain, broken):
        rows = mk({"local": eng}).models()
        assert [r["id"] for r in rows] == ["a", "b"]
        assert all(r["params_b"] is None and r["slow"] is False for r in rows)


def test_an_unavailable_local_engine_is_one_row_that_says_why(mk):
    eng = FakeEngine(models=["a", "b"], ok=False, why="Ollama is not running.")
    rows = mk({"local": eng}).models()
    assert rows == [{"engine": "local", "id": "", "available": False, "reason": "Ollama is not running."}]
    assert eng.calls["models"] == 0                    # an engine that says it is down is not asked for models
    raising = FakeEngine(models=["a"], raises=("available",))
    row = mk({"local": raising}).models()[0]
    assert row["available"] is False and "RuntimeError" in row["reason"]


def test_an_engine_whose_list_raises_offers_nothing(mk):
    assert mk({"local": FakeEngine(models=["a"], raises=("models",))}).models() == []


def test_the_scripted_key_is_used_only_when_it_is_allowed(mk):
    scripted = FakeEngine(name="fake", scripts={"f1": say("1"), "f2": say("2")})
    local = FakeEngine(scripts={"a": say("A")})
    closed = mk({"local": local, "fake": scripted})
    assert [r["id"] for r in closed.models()] == ["a"] and scripted.calls["models"] == 0
    opened = mk({"local": local, "fake": scripted}, local_engines={"local", "fake"})
    assert [r["id"] for r in opened.models()] == ["a", "f1", "f2"]
    run = finish(opened.start(MSG, ["a", "f1"]))
    assert [ln.engine_name for ln in run.lanes] == ["local", "fake"] and states(run) == [core.DONE] * 2


def test_lease_hooks_bracket_every_lane_and_a_raising_hook_is_harmless(mk):
    events = []
    eng = three()
    comparer = mk({"local": eng}, on_lane_start=lambda t: events.append(("start", t)),
                  on_lane_end=lambda t: events.append(("end", t)))
    run = finish(comparer.start(MSG, ["a", "b"]))
    rid = run.run_id
    assert events == [("start", rid + "-0"), ("end", rid + "-0"), ("start", rid + "-1"), ("end", rid + "-1")]

    def boom(token):
        raise RuntimeError("broker down")

    run = finish(mk({"local": three()}, on_lane_start=boom, on_lane_end=boom).start(MSG, ["a", "b"]))
    assert states(run) == [core.DONE, core.DONE]


def test_the_lease_is_returned_even_when_the_lane_raises(mk):
    events = []
    eng = FakeEngine(scripts={"a": [("raise", "x")], "b": say("B")})
    comparer = mk({"local": eng}, on_lane_start=lambda t: events.append("start"),
                  on_lane_end=lambda t: events.append("end"))
    finish(comparer.start(MSG, ["a", "b"]))
    assert events == ["start", "end", "start", "end"]


def test_old_runs_are_trimmed_but_the_active_one_never_is(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng}, keep_runs=2)
    for _ in range(3):
        eng.release["a"].set()
        finish(comparer.start(MSG, ["a", "b"]))
    assert len(comparer._runs) <= 3
    eng.release["a"].clear()
    live = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    assert len(comparer._runs) <= 2 and comparer.get(live.run_id) is live
    with pytest.raises(Refused) as ei:
        comparer.get("cmp-1")                         # the oldest finished run was dropped
    assert ei.value.code == core.NO_SUCH_RUN
    eng.release["a"].set()
    finish(live)


def test_with_keep_runs_zero_the_active_run_is_still_held(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    comparer = mk({"local": eng}, keep_runs=0)
    run = comparer.start(MSG, ["a", "b"])
    assert eng.started["a"].wait(WAIT)
    assert comparer.get(run.run_id) is run
    eng.release["a"].set()
    finish(run)


def test_a_thread_that_cannot_start_leaves_no_active_run(mk, monkeypatch):
    class NoThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            raise OSError("no more threads")

    monkeypatch.setattr(core, "threading", types.SimpleNamespace(
        Thread=NoThread, RLock=threading.RLock, Lock=threading.Lock, Event=threading.Event))
    eng = three()
    comparer = mk({"local": eng})
    with pytest.raises(OSError):
        comparer.start(MSG, ["a", "b"])
    assert comparer.busy() is None and len(comparer._runs) == 0 and comparer._active is None
    assert eng.calls["stream"] == 0


def test_choosing_an_answer_follows_the_rules(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B"), "c": [("text", "p")]})
    comparer = mk({"local": eng})
    run = comparer.start(MSG, ["b", "c", "a"])
    assert eng.started["a"].wait(WAIT)
    with pytest.raises(Refused) as ei:
        comparer.mark_picked(run, "b")
    assert ei.value.code == core.NOT_FINISHED
    eng.release["a"].set()
    finish(run)
    for model, code in (("zzz", core.NO_SUCH_LANE), ("c", core.NOT_PICKABLE)):
        with pytest.raises(Refused) as ei:
            comparer.mark_picked(run, model)
        assert ei.value.code == code
    lane = comparer.mark_picked(run, "b")
    assert lane.picked is True and run.picked == "b"
    with pytest.raises(Refused) as ei:
        comparer.mark_picked(run, "a")
    assert ei.value.code == core.ALREADY_PICKED
    comparer.unpick(run)
    assert run.picked is None and lane.picked is False
    assert comparer.mark_picked(run, "a").model == "a"  # and the claim can be made again after a release


def test_parse_params_b():
    assert parse_params_b("7.6B") == pytest.approx(7.6)
    assert parse_params_b("7.6b") == pytest.approx(7.6)
    assert parse_params_b("137M") == pytest.approx(0.137)
    assert parse_params_b("500K") == pytest.approx(0.0005)
    for junk in ("", None, "B", "7", "x7B", "abcM", "7.6.1B", "lots", 7, "  "):
        assert parse_params_b(junk) is None             # unknown is not zero


def test_results_are_json_safe_and_hold_no_engine_object(mk):
    eng = three()
    comparer = mk({"local": eng}, blocker=None)
    run = finish(comparer.start(MSG, ["a", "b"]))
    blob = json.dumps([run.snapshot(), run.record(), comparer.models()])
    assert "FakeEngine" not in blob and "_engine" not in blob and "_started" not in blob
    assert all(not k.startswith("_") for ln in run.lanes for k in ln.to_dict())


# ---- the gate ----------------------------------------------------------------------------------------------

class FakeStore:
    """`assistant.store.ConvStore`'s methods and signatures, in memory. `fail_once` names a write that
    raises the first time it is called."""

    def __init__(self, convs=None, fail_once=()):
        self.convs = {cid: {"id": cid, "history": list(h)} for cid, h in (convs or {}).items()}
        self.fail_once = set(fail_once)
        self.writes = []
        self._n = 0

    def ops(self):
        return [w[0] for w in self.writes]

    def _maybe_fail(self, op):
        if op in self.fail_once:
            self.fail_once.discard(op)
            raise RuntimeError("disk said no to " + op)

    def get(self, conv_id):
        return self.convs.get(conv_id)

    def history(self, conv_id):
        return [dict(m) for m in self.convs[conv_id]["history"]]

    def new(self, title=None, model=None):
        self._maybe_fail("new")
        self._n += 1
        cid = "new%d" % self._n
        self.convs[cid] = {"id": cid, "history": []}
        self.writes.append(("new", cid, model))
        return {"id": cid}

    def add_user(self, conv_id, text):
        self._maybe_fail("add_user")
        self.writes.append(("add_user", conv_id, text))
        return {"id": "u%d" % len(self.writes)}

    def start_assistant(self, conv_id, model):
        self._maybe_fail("start_assistant")
        self._n += 1
        mid = "msg%d" % self._n
        self.writes.append(("start_assistant", conv_id, model, mid))
        return mid

    def finish_assistant(self, msg_id, text, *, tokens_in=None, tokens_out=None, stop_reason=None):
        self._maybe_fail("finish_assistant")
        self.writes.append(("finish_assistant", msg_id, text, tokens_in, tokens_out, stop_reason))


def make_desk(mk, engines=None, store=None, context_fn=None, **kw):
    engines = engines if engines is not None else {"local": three()}
    store = store if store is not None else FakeStore({"c1": []})
    return CompareDesk(mk(engines, **kw), store, context_fn=context_fn), engines, store


def run_of(desk, out):
    assert out["ok"], out
    return finish(desk.comparer.get(out["run_id"]))


def test_start_poll_and_a_run_that_writes_nothing_until_the_owner_picks(mk):
    desk, engines, store = make_desk(mk)
    out = desk.compare_start("hello", ["a", "b"], conv_id="c1")
    assert out["ok"] is True and out["count"] == 2 and out["sequential"] is True
    run = run_of(desk, out)
    polled = desk.compare_poll(out["run_id"])
    assert polled["ok"] and polled["state"] == "finished"
    assert [ln["text"] for ln in polled["lanes"]] == ["A", "B"]
    assert store.writes == []                           # a discarded comparison leaves the chat as it was
    assert run.picked is None


def test_pick_writes_the_question_then_the_chosen_answer_exactly_once(mk):
    desk, engines, store = make_desk(mk)
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    res = desk.compare_pick(run.run_id, "b")
    assert res == {"ok": True, "conv_id": "c1", "msg_id": res["msg_id"], "model": "b", "continue_with": "b"}
    assert store.ops() == ["add_user", "start_assistant", "finish_assistant"]
    assert store.writes[0] == ("add_user", "c1", "hello")
    assert store.writes[1][2] == "b"
    assert store.writes[2] == ("finish_assistant", res["msg_id"], "B", 3, 5, "end_turn")
    again = desk.compare_pick(run.run_id, "a")
    assert again["ok"] is False and again["refused"] == core.ALREADY_PICKED
    assert store.ops() == ["add_user", "start_assistant", "finish_assistant"]
    snap = desk.compare_poll(run.run_id)
    assert snap["picked"] == "b" and [ln["picked"] for ln in snap["lanes"]] == [False, True]


def test_a_new_chat_is_created_at_the_pick_not_before(mk):
    desk, engines, store = make_desk(mk)
    run = run_of(desk, desk.compare_start("hello", ["a", "b"]))        # no conv_id
    assert store.writes == []
    res = desk.compare_pick(run.run_id, "a")
    assert res["ok"] and res["conv_id"].startswith("new")
    assert store.ops() == ["new", "add_user", "start_assistant", "finish_assistant"]
    assert store.writes[0][2] == "a"                   # the chat is born with the model that was kept


def test_pick_before_the_run_finished_is_refused_and_writes_nothing(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    desk, _, store = make_desk(mk, {"local": eng})
    out = desk.compare_start("hello", ["a", "b"], conv_id="c1")
    assert eng.started["a"].wait(WAIT)
    res = desk.compare_pick(out["run_id"], "a")
    assert res["ok"] is False and res["refused"] == core.NOT_FINISHED and store.writes == []
    eng.release["a"].set()
    finish(desk.comparer.get(out["run_id"]))


def test_after_a_stop_what_finished_can_be_kept_and_what_did_not_cannot(mk):
    eng = FakeEngine(scripts={"a": say("A"), "b": [("text", "p"), ("hold",), ("done", {})]})
    desk, _, store = make_desk(mk, {"local": eng})
    out = desk.compare_start("hello", ["a", "b"], conv_id="c1")
    assert eng.started["b"].wait(WAIT)
    stopped = desk.compare_stop(out["run_id"])
    assert stopped["ok"]
    finish(desk.comparer.get(out["run_id"]))
    refused = desk.compare_pick(out["run_id"], "b")
    assert refused["ok"] is False and refused["refused"] == core.NOT_PICKABLE and store.writes == []
    assert desk.compare_pick(out["run_id"], "a")["ok"] is True
    assert store.writes[-1][2] == "A"


def test_pick_of_a_model_that_was_not_in_the_run_or_a_run_that_is_gone(mk):
    desk, _, store = make_desk(mk)
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    res = desk.compare_pick(run.run_id, "zzz")
    assert res["ok"] is False and res["refused"] == core.NO_SUCH_LANE
    res = desk.compare_pick("cmp-404", "a")
    assert res["ok"] is False and res["refused"] == core.NO_SUCH_RUN
    assert store.writes == []


def test_a_failed_write_gives_the_claim_back_and_the_question_is_written_once(mk):
    desk, _, store = make_desk(mk, store=FakeStore({"c1": []}, fail_once={"start_assistant"}))
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    with pytest.raises(RuntimeError, match="start_assistant"):
        desk.compare_pick(run.run_id, "a")
    assert run.picked is None and run.lanes[0].picked is False
    assert store.ops() == ["add_user"]
    res = desk.compare_pick(run.run_id, "a")
    assert res["ok"]
    assert store.ops() == ["add_user", "start_assistant", "finish_assistant"]   # add_user once, not twice


def test_a_failure_after_the_row_began_finishes_that_same_row_and_only_for_that_model(mk):
    desk, _, store = make_desk(mk, store=FakeStore({"c1": []}, fail_once={"finish_assistant"}))
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    with pytest.raises(RuntimeError, match="finish_assistant"):
        desk.compare_pick(run.run_id, "a")
    assert store.ops() == ["add_user", "start_assistant"]
    other = desk.compare_pick(run.run_id, "b")           # another model's words under a's label: refused
    assert other["ok"] is False and other["refused"] == RETRY_SAME_ANSWER and "a" in other["error"]
    assert run.picked is None and store.ops() == ["add_user", "start_assistant"]
    res = desk.compare_pick(run.run_id, "a")
    assert res["ok"] and res["msg_id"] == store.writes[1][3]
    assert store.ops() == ["add_user", "start_assistant", "finish_assistant"]
    assert store.writes[2][2] == "A"


def test_a_failure_to_create_the_chat_can_be_retried(mk):
    desk, _, store = make_desk(mk, store=FakeStore({}, fail_once={"new"}))
    run = run_of(desk, desk.compare_start("hello", ["a", "b"]))
    with pytest.raises(RuntimeError):
        desk.compare_pick(run.run_id, "b")
    assert store.writes == [] and run.picked is None
    res = desk.compare_pick(run.run_id, "a")             # nothing was begun, so any lane may be tried
    assert res["ok"] and store.ops() == ["new", "add_user", "start_assistant", "finish_assistant"]


def test_history_the_new_message_and_the_context_function_reach_every_lane(mk):
    history = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "reply"}]
    engines = {"local": three()}
    store = FakeStore({"c1": history})
    desk, _, _ = make_desk(mk, engines, store,
                           context_fn=lambda cid, h: [{"role": "system", "content": "SYS-" + cid}] + list(h))
    run_of(desk, desk.compare_start("  hello  ", ["a", "b"], conv_id="c1"))
    expect = [{"role": "system", "content": "SYS-c1"}, *history, {"role": "user", "content": "hello"}]
    assert [r["messages"] for r in engines["local"].seen] == [expect, expect]
    assert store.writes == []


def test_a_broken_context_function_costs_the_prompt_not_the_run(mk):
    def broken(cid, history):
        raise RuntimeError("prompt helper down")

    desk, engines, _ = make_desk(mk, context_fn=broken)
    run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    assert engines["local"].seen[0]["messages"] == MSG


def test_a_missing_conversation_is_refused_with_no_engine_call_and_no_write(mk):
    desk, engines, store = make_desk(mk)
    out = desk.compare_start("hello", ["a", "b"], conv_id="gone")
    assert out["ok"] is False and out["refused"] == "no_such_conversation" and out["error"]
    assert engines["local"].calls["stream"] == 0 and store.writes == []
    assert desk.comparer.busy() is None


def test_export_keeps_a_code_fence_untouched_and_refuses_an_unknown_run(mk):
    fenced = "Here:\n```python\nprint(1)\n```\nDone."
    eng = FakeEngine(scripts={"a": say(fenced), "b": say("B")})
    desk, _, _ = make_desk(mk, {"local": eng})
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    out = desk.compare_export(run.run_id)
    assert out["ok"] and fenced in out["markdown"]
    gone = desk.compare_export("cmp-404")
    assert gone["ok"] is False and gone["refused"] == core.NO_SUCH_RUN and "markdown" not in gone


def test_the_models_list_says_the_rules_the_page_needs(mk):
    desk, _, _ = make_desk(mk)
    out = desk.compare_models()
    assert out["ok"] and [r["id"] for r in out["items"]] == ["a", "b", "c"]
    assert (out["min"], out["max"], out["sequential"], out["local_only"], out["busy"]) == (2, 4, True, True, None)
    json.dumps(out)


@pytest.mark.parametrize("method,args", [
    ("compare_poll", ("cmp-404",)), ("compare_stop", ("cmp-404",)), ("compare_skip", ("cmp-404",)),
    ("compare_pick", ("cmp-404", "a")), ("compare_export", ("cmp-404",)),
])
def test_a_bad_run_id_is_a_dict_with_ok_false_never_an_exception(mk, method, args):
    desk, _, store = make_desk(mk)
    out = getattr(desk, method)(*args)
    assert out["ok"] is False and out["refused"] == core.NO_SUCH_RUN and out["error"]
    assert store.writes == []


@pytest.mark.parametrize("args,code", [
    (("", ["a", "b"]), core.EMPTY_PROMPT),
    (("   ", ["a", "b"]), core.EMPTY_PROMPT),
    (("x", None), core.TOO_FEW),
    (("x", ["a"]), core.TOO_FEW),
    (("x", "a"), core.TOO_FEW),                          # a bare string is ONE model, not letters
    (("x", ["a", "claude-sonnet"]), core.NOT_LOCAL),
    (("x", ["a", "zzz"]), core.NOT_INSTALLED),
    (("x", list("abcde")), core.TOO_MANY),
])
def test_start_refusals_come_back_as_dicts_and_run_nothing(mk, args, code):
    desk, engines, store = make_desk(mk, {"local": FakeEngine(scripts={m: say(m) for m in "abcde"})})
    out = desk.compare_start(*args)
    assert out["ok"] is False and out["refused"] == code and out["error"]
    assert engines["local"].calls["stream"] == 0 and store.writes == [] and desk.busy() is None


def test_every_bridge_method_the_doc_lists_exists_and_no_other_is_public():
    names = sorted(n for n in dir(CompareDesk) if n.startswith("compare_"))
    assert names == ["compare_export", "compare_models", "compare_pick", "compare_poll",
                     "compare_skip", "compare_start", "compare_stop"]
    other_public = sorted(n for n in dir(CompareDesk) if not n.startswith(("_", "compare_")))
    assert other_public == ["busy", "shutdown"]          # the two the Api calls itself, not the page


def test_poll_with_a_version_it_cannot_read_gets_everything(mk):
    desk, _, _ = make_desk(mk)
    run = run_of(desk, desk.compare_start("hello", ["a", "b"], conv_id="c1"))
    for bad in ("abc", [], {}, object()):
        out = desk.compare_poll(run.run_id, bad)
        assert out["ok"] and out["changed"] is True and len(out["lanes"]) == 2
    quiet = desk.compare_poll(run.run_id, str(run.version))      # the page may send it as text
    assert quiet["ok"] and quiet["changed"] is False


def test_busy_and_shutdown_are_what_the_api_calls(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    desk, _, store = make_desk(mk, {"local": eng})
    assert desk.busy() is None
    out = desk.compare_start("hello", ["a", "b"], conv_id="c1")
    assert eng.started["a"].wait(WAIT)
    assert desk.busy() == "A model comparison is running."
    assert desk.compare_models()["busy"] == "A model comparison is running."
    desk.shutdown()
    run = finish(desk.comparer.get(out["run_id"]))
    assert states(run) == [core.CANCELLED, core.CANCELLED] and desk.busy() is None
    assert store.writes == [] and eng.cancel_flag is False


def test_skip_through_the_gate(mk):
    eng = FakeEngine(scripts={"a": [("hold",), ("done", {})], "b": say("B")})
    desk, _, _ = make_desk(mk, {"local": eng})
    out = desk.compare_start("hello", ["a", "b"], conv_id="c1")
    assert eng.started["a"].wait(WAIT)
    assert desk.compare_skip(out["run_id"])["ok"]
    run = finish(desk.comparer.get(out["run_id"]))
    assert states(run) == [core.SKIPPED, core.DONE]
    late = desk.compare_skip(out["run_id"])
    assert late["ok"] is False and late["refused"] == core.NOT_RUNNING


# ---- build_gate: how the app's Api is wired in -----------------------------------------------------------------

class FakePanes:
    def __init__(self):
        self.events = []

    def turn_started(self, turn_id):
        self.events.append(("start", turn_id))

    def turn_finished(self, turn_id):
        self.events.append(("end", turn_id))


class FakeApi:
    def __init__(self, engines, store=None, panes=None, turn=None):
        self.engines = engines
        self.store = store if store is not None else FakeStore({"c1": []})
        self.panes = panes
        self._turn = turn


def live_turn(running):
    done = threading.Event()
    if not running:
        done.set()
    return types.SimpleNamespace(done=done)


def test_build_gate_without_scripting_never_asks_the_scripted_engine(mk):
    local = FakeEngine(scripts={"a": say("A"), "b": say("B")})
    fake = FakeEngine(name="fake", scripts={"f1": say("1"), "f2": say("2")})
    desk = build_gate(FakeApi({"local": local, "fake": fake}), scripted=False)
    try:
        assert [r["id"] for r in desk.compare_models()["items"]] == ["a", "b"]
        out = desk.compare_start("x", ["f1", "f2"])
        assert out["ok"] is False and out["refused"] == core.NOT_INSTALLED
        assert fake.calls == {"available": 0, "models": 0, "catalog": 0, "stream": 0, "cancel": 0}
    finally:
        desk.shutdown()


def test_build_gate_with_scripting_allows_the_scripted_engine_and_only_it(mk):
    fake = FakeEngine(name="fake", scripts={"f1": say("1"), "f2": say("2")})
    cloud = FakeEngine(name="claude", scripts={"c1": say("c")})
    desk = build_gate(FakeApi({"fake": fake, "claude": cloud}), scripted=True)
    assert [r["id"] for r in desk.compare_models()["items"]] == ["f1", "f2"]
    run = run_of(desk, desk.compare_start("x", ["f1", "f2"]))
    assert states(run) == [core.DONE, core.DONE]
    assert cloud.calls == {"available": 0, "models": 0, "catalog": 0, "stream": 0, "cancel": 0}


def test_a_live_chat_turn_blocks_a_comparison_and_a_finished_one_does_not():
    eng = three()
    api = FakeApi({"local": eng}, turn=live_turn(True))
    desk = build_gate(api, scripted=False)
    out = desk.compare_start("x", ["a", "b"])
    assert out["ok"] is False and out["refused"] == core.BUSY and "chat turn is running" in out["error"]
    assert eng.calls["stream"] == 0
    api._turn.done.set()
    assert run_of(desk, desk.compare_start("x", ["a", "b"]))
    api._turn = None
    assert run_of(desk, desk.compare_start("x", ["a", "b"]))


def test_a_turn_we_cannot_read_is_busy_not_free():
    eng = three()
    api = FakeApi({"local": eng}, turn=object())         # no `.done`: cannot tell
    out = build_gate(api, scripted=False).compare_start("x", ["a", "b"])
    assert out["ok"] is False and out["refused"] == core.BUSY and "could not tell" in out["error"]
    assert eng.calls["stream"] == 0


def test_the_gpu_lease_broker_is_told_per_lane_even_if_it_appears_after_the_gate():
    api = FakeApi({"local": three()}, panes=None)         # built before the panes desk exists
    desk = build_gate(api, scripted=False)
    api.panes = FakePanes()
    run = run_of(desk, desk.compare_start("x", ["a", "b"]))
    rid = run.run_id
    assert api.panes.events == [("start", rid + "-0"), ("end", rid + "-0"),
                                ("start", rid + "-1"), ("end", rid + "-1")]


@pytest.mark.parametrize("panes", [None, object(), types.SimpleNamespace(turn_started=5, turn_finished=None)])
def test_a_missing_or_odd_lease_broker_is_harmless(panes):
    desk = build_gate(FakeApi({"local": three()}, panes=panes), scripted=False)
    assert states(run_of(desk, desk.compare_start("x", ["a", "b"]))) == [core.DONE, core.DONE]


def test_a_broker_that_raises_costs_the_hook_not_the_lane():
    class Bad:
        def turn_started(self, t):
            raise RuntimeError("down")

        def turn_finished(self, t):
            raise RuntimeError("down")

    desk = build_gate(FakeApi({"local": three()}, panes=Bad()), scripted=False)
    assert states(run_of(desk, desk.compare_start("x", ["a", "b"]))) == [core.DONE, core.DONE]


def test_the_chats_own_system_prompt_is_used_when_the_api_has_one():
    eng = three()
    api = FakeApi({"local": eng})
    api._chat_prompt_context = lambda cid, history: [{"role": "system", "content": "BE BRIEF"}] + list(history)
    desk = build_gate(api, scripted=False)
    run_of(desk, desk.compare_start("x", ["a", "b"], conv_id="c1"))
    assert eng.seen[0]["messages"] == [{"role": "system", "content": "BE BRIEF"},
                                       {"role": "user", "content": "x"}]


def test_build_gate_refuses_an_api_that_lacks_what_it_needs():
    with pytest.raises(RuntimeError):
        build_gate(types.SimpleNamespace(engines=None, store=FakeStore()), scripted=False)
    with pytest.raises(RuntimeError):
        build_gate(types.SimpleNamespace(engines={}, store=None), scripted=False)
    with pytest.raises(RuntimeError):
        build_gate(types.SimpleNamespace(engines={}, store=object()), scripted=False)
    with pytest.raises(RuntimeError):
        build_gate(types.SimpleNamespace(engines=[], store=FakeStore()), scripted=False)


# ---- Law 9: the package cannot reach the network, a process or a file -----------------------------------------

BANNED_MODULES = {"socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp", "smtplib", "ftplib",
                  "subprocess", "webbrowser", "ctypes", "importlib", "os", "shutil", "pathlib", "tempfile"}
BANNED_CALLS = {"__import__", "eval", "exec", "open"}


def forbidden_in(source: str) -> list[str]:
    """Names of every import or call in `source` that could reach outside this process."""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            hits += [a.name for a in node.names if a.name.split(".")[0] in BANNED_MODULES]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and (node.module or "").split(".")[0] in BANNED_MODULES:
                hits.append(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            hits.append(node.func.id + "()")
    return hits


def test_the_scan_can_see_what_it_looks_for():
    """Positive control. If this fails the real scan below proves nothing."""
    bad = ("import socket\nfrom urllib.request import urlopen\nimport importlib.util\n"
           "from os import path\nx = __import__('socket')\nopen('f')\neval('1')\n")
    assert forbidden_in(bad) == ["socket", "urllib.request", "importlib.util", "os", "__import__()",
                                 "open()", "eval()"]
    assert forbidden_in("import threading\nfrom .core import X\nfrom typing import Callable\n") == []


def test_the_package_imports_nothing_that_can_leave_the_machine():
    pkg = os.path.dirname(os.path.abspath(modelcompare.__file__))
    files = sorted(glob.glob(os.path.join(pkg, "*.py")))
    assert {os.path.basename(f) for f in files} >= {"__init__.py", "core.py", "gate.py"}
    for path in files:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        assert source.strip(), path
        assert forbidden_in(source) == [], path


def test_the_mockup_has_no_network_reference_and_the_scan_sees_one():
    def external(html):
        return (re.findall(r"://", html) + re.findall(r"""(?:src|href|action)\s*=\s*["']?//""", html)
                + re.findall(r"@import|url\(\s*[\"']?(?:https?:)?//|<link\b|<img\b|<iframe\b|<form\b|"
                             r"fetch\(|XMLHttpRequest|WebSocket|sendBeacon|EventSource", html, re.I))

    path = os.path.join(ROOT, "docs", "mockups", "model-compare.html")
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    assert "Compare" in html and len(html) > 2000        # we read the real file, not an empty one
    assert external(html) == []
    assert external('<a href="http://example.com">x</a>') == ["://"]          # positive controls
    assert external('<script>fetch("/x")</script>') == ["fetch("]
    assert external('<img src="//cdn/x.png">') != []


def test_the_scope_doc_names_every_bridge_method_and_what_was_not_verified():
    path = os.path.join(ROOT, "docs", "NOVAHOS_MODEL_COMPARE.md")
    with open(path, encoding="utf-8") as fh:
        doc = fh.read()
    for name in ("compare_models", "compare_start", "compare_poll", "compare_stop", "compare_skip",
                 "compare_pick", "compare_export"):
        assert name in doc, name
    for must_say in ("UNTESTED IN THE REAL WINDOW", "local only", "mockups/model-compare.html"):
        assert must_say in doc, must_say
