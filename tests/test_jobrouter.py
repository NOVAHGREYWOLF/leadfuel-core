"""NODE job router (fold-c-jobrouter-build): route.py places one real job class, and a host it cannot
vouch for is never picked.

Every "never" below has a positive control next to it: the same fixture, one fact changed, and the
host IS picked. A check that cannot be made to say yes proves nothing when it says no.

Machines in these tests are fakes: a registry entry plus a recording runner. Nothing here connects
to anything; a test monkeypatches subprocess.run to fail loudly where ssh could have been reached.
"""
import ast
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
from collections import Counter

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "node", "jobrouter", "route.py")
_spec = importlib.util.spec_from_file_location("jobrouter_route", _PATH)
r = importlib.util.module_from_spec(_spec)
sys.modules["jobrouter_route"] = r
_spec.loader.exec_module(r)

NOW = 1795305660.0                       # 2026-11-22T00:01:00Z, the minute after a real feed sample
HOSTS_JSON = os.path.join(os.path.dirname(_PATH), "hosts.json")
CLASSES_JSON = os.path.join(os.path.dirname(_PATH), "classes.json")
REAL_CLASS = "standby-refresh-catchup"


def iso(epoch):
    return r.utc_iso(epoch)


def row(hid, cpu=5.0, ram=20.0, age=60, threads=16, state="up", **over):
    d = {"id": hid, "name": hid, "threads": threads, "cpu_now_pct": cpu, "cpu15_pct": cpu, "ram_pct": ram,
         "ram_total_gb": 62.0, "facts_age_s": age, "collected": iso(NOW - age), "state": state,
         "state_reason": "facts %ds old" % age, "memory_bound": False}
    d.update(over)
    return d


def feed_doc(rows, file_age=30, **over):
    gen = NOW - file_age
    d = {"schema": "utilization-1", "generated": iso(gen), "generated_ts": int(gen), "window_s": 900,
         "stale_after_s": 360, "hosts": rows}
    d.update(over)
    return d


def real_feed_rows():
    """All nine ids the live feed listed on 2026-11-22 (first five exact; the rest as the handoffs name them)."""
    return [row("overlord", 3.1, 28.2, 120, 36), row("ci-runners", 0.3, 6.2, 120, 12), row("pve-ng", 17.3, 4.0, 240),
            row("pve-r620", 1.8, 9.0, 240, 24), row("novahub-pg", 0.7, 3.5, 119, 4), row("GREYWOLF", 25.0, 40.0, 120),
            row("SURFACE", 9.0, 85.0, 120, 8), row("pve-od", None, None, 900000, None, "unknown", cpu15_pct=None),
            row("pve-r610", None, None, 900000, None, "unknown", cpu15_pct=None)]


def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj))
    return str(path)


def H(hid, threads=16, ceiling=80, always_on=True, thermal=False, accepts=True, in_cluster=True, mode="none",
      enabled=True, gpu=(), **over):
    d = {"id": hid, "threads": threads, "ram_gb": 62, "gpu": list(gpu), "always_on": always_on,
         "thermal_limited": thermal, "ceiling_cpu_pct": ceiling, "in_cluster": in_cluster, "accepts_jobs": accepts}
    if mode == "ssh":
        d["exec"] = {"mode": "ssh", "alias": hid, "enabled": enabled}
    else:
        d["exec"] = {"mode": mode}
    d.update(over)
    return d


def C(eligible, kind="cpu", argv=None, **over):
    d = {"kind": kind, "eligible_hosts": list(eligible), "argv": [sys.executable, "-c", "print('ran')"] if argv is None else argv,
         "timeout_s": 30, "needs": {"threads": 1}}
    d.update(over)
    return d


class Env:
    """A registry, classes and feed on disk, and a place to put queue state."""

    def __init__(self, tmp, hosts, classes, rows=None, file_age=30, **feed_over):
        self.tmp = tmp
        self.hosts = write(tmp / "hosts.json", {"schema": "jobrouter-hosts-1", "hosts": hosts})
        self.classes = write(tmp / "classes.json", {"schema": "jobclasses-1", "classes": classes})
        self.feed = str(tmp / "feed.json")
        self.state = str(tmp / "state")
        if rows is not None:
            self.set_feed(rows, file_age, **feed_over)

    def set_feed(self, rows, file_age=30, **over):
        write(self.feed, feed_doc(rows, file_age, **over))

    def cli(self, *args, here="overlord", runner=None):
        out = io.StringIO()
        argv = ["--feed", self.feed, "--hosts", self.hosts, "--classes", self.classes,
                "--state-dir", self.state, "--here", here] + list(args)
        code = r.main(argv, runner=runner, out=out, clock=lambda: NOW)
        return code, out.getvalue()

    def ctx(self, here="overlord", runner=None):
        hosts, stale = r.load_registry(self.hosts)
        return r.Ctx(hosts, r.load_classes(self.classes, hosts), stale, self.feed, self.state, here,
                     runner or FakeMachines(), lambda: NOW)

    def log(self):
        """Read the log the way another program would: plain json, line by line."""
        path = os.path.join(self.state, "placements.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


class FakeMachines:
    """The second machine. Records every job it is asked to run and answers ok."""

    def __init__(self, status="ok", code=0):
        self.runs = []
        self.status, self.code = status, code

    def __call__(self, host, cls):
        self.runs.append((host.id, list(cls.argv)))
        return r.RunResult(self.status, self.code, 0.5, "fake output", "", iso(NOW), iso(NOW + 1))


@pytest.fixture
def no_ssh(monkeypatch):
    """Any attempt to start a process fails the test: proves a code path never reached ssh."""
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise AssertionError("subprocess.run was called: %r" % (a,))
    monkeypatch.setattr(subprocess, "run", boom)
    return calls


def two_hosts(**fake):
    return [H("overlord", 36, mode="local"), H("fakebox", 24, mode="ssh", **fake)]


# ----------------------------------------------------------------------- the real registry, real class

def test_real_registry_places_the_real_class_on_overlord(tmp_path):
    e = Env(tmp_path, [], {})
    e.hosts, e.classes = HOSTS_JSON, CLASSES_JSON
    e.set_feed(real_feed_rows())
    code, text = e.cli("pick", REAL_CLASS)
    assert code == 0 and text.startswith("PICK overlord"), text


def test_real_class_waits_when_its_source_has_no_fresh_reading(tmp_path):
    e = Env(tmp_path, [], {})
    e.hosts, e.classes = HOSTS_JSON, CLASSES_JSON
    rows = [x for x in real_feed_rows() if x["id"] != "GREYWOLF"] + [row("GREYWOLF", 25, 40, 600)]
    e.set_feed(rows)                                    # GREYWOLF's facts are 10 minutes old: unknown
    code, text = e.cli("pick", REAL_CLASS)
    assert code == 3 and "dependency" in text and "GREYWOLF" in text, text
    e.set_feed(real_feed_rows())                        # positive control: fresh facts, same everything else
    assert e.cli("pick", REAL_CLASS)[0] == 0


def test_real_files_agree_with_a_feed_of_the_nine_hosts(tmp_path):
    e = Env(tmp_path, [], {})
    e.hosts, e.classes = HOSTS_JSON, CLASSES_JSON
    e.set_feed(real_feed_rows())
    code, text = e.cli("check")
    assert code == 0 and text.startswith("CHECK OK"), text


def test_check_names_a_host_the_feed_has_and_the_registry_lacks_and_the_reverse(tmp_path):
    e = Env(tmp_path, [], {})
    e.hosts, e.classes = HOSTS_JSON, CLASSES_JSON
    e.set_feed(real_feed_rows() + [row("mystery-box")])
    code, text = e.cli("check")
    assert code == 1 and "'mystery-box' is in the feed but not in the registry" in text
    e.set_feed([x for x in real_feed_rows() if x["id"] != "pve-ng"])
    code, text = e.cli("check")
    assert code == 1 and "'pve-ng' is in the registry (in_feed) but not in the feed" in text


def test_check_cannot_pass_without_a_feed(tmp_path):
    e = Env(tmp_path, [], {})
    e.hosts, e.classes = HOSTS_JSON, CLASSES_JSON
    code, text = e.cli("check")
    assert code == 2 and "not found" in text            # an unreadable feed is an error, never "CHECK OK"


def test_closed_hosts_are_never_picked_even_if_a_class_names_them(tmp_path):
    hosts = [H("overlord", 36, mode="local"), H("pve-od", 16, in_cluster=False, mode="ssh")]
    e = Env(tmp_path, hosts, {"job": C(["overlord", "pve-od"])}, [row("overlord", 90.0, threads=36), row("pve-od", 0.0)])
    code, text = e.cli("pick", "job")
    assert code == 3 and "closed" in text and "pve-od" in text   # overlord is full (90% > ceiling), od is closed


# ------------------------------------------------------------------------- unknown is never picked

@pytest.mark.parametrize("age,expect", [(300, True), (359, True), (361, False), (4000, False)])
def test_a_host_with_facts_older_than_six_minutes_is_never_picked(tmp_path, age, expect):
    # fakebox has every advantage (idle, 24 threads); overlord is busy. Only the age of fakebox's facts changes.
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord", "fakebox"])},
            [row("overlord", 70.0, threads=36), row("fakebox", 1.0, age=age, threads=24)], file_age=0)
    code, text = e.cli("pick", "job", "--json")
    d = json.loads(text)
    assert (d["host"] == "fakebox") is expect
    if not expect:
        assert d["host"] == "overlord"                  # a busy host that is fresh beats an idle one that is not


def test_unknown_state_is_never_picked_whatever_numbers_it_carries(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), row("fakebox", 0.0, state="unknown")])
    code, text = e.cli("pick", "job")
    assert code == 3 and "unknown" in text
    e.set_feed([row("overlord"), row("fakebox", 0.0, state="up")])      # positive control
    assert e.cli("pick", "job")[0] == 0


def test_a_host_the_feed_does_not_list_is_unknown(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord")])
    code, text = e.cli("pick", "job")
    assert code == 3 and "not listed in the utilization feed" in text


def test_a_stale_copy_of_the_whole_file_leaves_nothing_to_pick(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord", "fakebox"])}, [row("overlord"), row("fakebox")], file_age=700)
    # every row still says state up and carries a plausible age field, copied from ten minutes ago
    code, text = e.cli("pick", "job")
    assert code == 3 and "feed file itself is 700 s old" in text
    e.set_feed([row("overlord"), row("fakebox")], file_age=30)        # positive control
    assert e.cli("pick", "job")[0] == 0


def test_the_older_of_two_ages_wins(tmp_path):
    stale_field = row("fakebox", 1.0, age=60)
    stale_field["facts_age_s"] = 5000                                  # the 'collected' stamp says fresh, the field says not
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), stale_field])
    assert e.cli("pick", "job")[0] == 3
    stale_field["facts_age_s"] = 60                                    # positive control
    e.set_feed([row("overlord"), stale_field])
    assert e.cli("pick", "job")[0] == 0


def test_timestamps_ahead_of_our_clock_are_not_trusted(tmp_path):
    ahead = row("fakebox", 1.0, collected=iso(NOW + 3600))              # collected an hour in the future
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), ahead])
    code, text = e.cli("pick", "job")
    assert code == 3 and "ahead of this clock" in text
    e.set_feed([row("overlord"), row("fakebox", 1.0, collected=iso(NOW + 30))], file_age=0)   # inside the slack: fine
    assert e.cli("pick", "job")[0] == 0


@pytest.mark.parametrize("field,junk", [("collected", "yesterday"), ("collected", "2026-11-22T00:00:00"),
                                        ("facts_age_s", "60"), ("facts_age_s", -5), ("cpu_now_pct", "12"),
                                        ("cpu15_pct", True)])
def test_a_field_that_is_present_but_unusable_makes_the_host_unknown(tmp_path, field, junk):
    broken = row("fakebox", 1.0)
    broken[field] = junk                  # the other fields are fine: a half-broken row is still not evidence
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), broken])
    code, text = e.cli("pick", "job")
    assert code == 3 and ("unusable" in text or "no CPU reading" in text), text
    e.set_feed([row("overlord"), row("fakebox", 1.0)])                  # positive control
    assert e.cli("pick", "job")[0] == 0


@pytest.mark.parametrize("over,needle", [({"generated_ts": "soon"}, "generated_ts is not a usable number"),
                                         ({"generated": "tomorrow"}, "not a time with a Z"),
                                         ({"generated_ts": None, "generated": None}, "no usable generation time")])
def test_a_feed_header_that_is_there_but_broken_is_an_error(tmp_path, over, needle):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord")], **over)
    code, text = e.cli("pick", "job")
    assert code == 2 and needle in text, text


def test_two_generation_stamps_that_disagree_the_older_wins(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), row("fakebox", 1.0)],
            generated=iso(NOW - 900))                                   # ts says 30 s ago, the text says 15 minutes ago
    code, text = e.cli("pick", "job")
    assert code == 3 and "facts are" in text
    e.set_feed([row("overlord"), row("fakebox", 1.0)])                  # positive control: they agree
    assert e.cli("pick", "job")[0] == 0


def test_a_job_file_whose_id_does_not_match_its_name_is_refused(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord", threads=36)])
    d = r.ensure_state(e.state)
    write(os.path.join(d["pending"], "evil.json"), {"id": "../../escape", "class": "job"})
    fake = FakeMachines()
    code, text = e.cli("dispatch", runner=fake)
    assert code == 2 and "job id does not match" in text and fake.runs == []


def test_a_row_with_no_collection_time_is_unknown(tmp_path):
    bare = row("fakebox", 1.0)
    del bare["collected"]
    del bare["facts_age_s"]
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), bare])
    code, text = e.cli("pick", "job")
    assert code == 3 and "no collection time" in text


@pytest.mark.parametrize("bad", [None, "12", True, -1, 101, float("nan")])
def test_a_cpu_reading_that_is_not_a_number_in_range_makes_the_host_unknown(tmp_path, bad):
    broken = row("fakebox", 1.0)
    broken["cpu15_pct"] = bad
    broken["cpu_now_pct"] = bad
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), broken])
    code, text = e.cli("pick", "job")
    assert code == 3 and "no CPU reading" in text


def test_the_busier_of_mean_and_now_counts(tmp_path):
    spike = row("fakebox", 2.0)
    spike["cpu_now_pct"] = 95.0                                        # mean is calm, right now it is not
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), spike])
    code, text = e.cli("pick", "job")
    assert code == 3 and "full" in text


# --------------------------------------------------------------------------- the feed cannot be read

@pytest.mark.parametrize("content,needle", [
    (None, "not found"), ("", "empty"), ("not json {", "not valid JSON"), ("[1, 2]", "not a JSON object"),
    ('{"schema": "utilization-2", "hosts": []}', "this router reads 'utilization-1'"),
    ('{"schema": "utilization-1"}', "no 'hosts' list"),
    ('{"schema": "utilization-1", "hosts": []}', "no usable generation time"),
])
def test_a_feed_that_cannot_be_read_is_an_error_that_names_why_and_there_is_no_default_host(tmp_path, content, needle):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord", "fakebox"])})
    if content is not None:
        write(e.feed, content)
    code, text = e.cli("pick", "job")
    assert code == 2 and text.startswith("ERROR:") and needle in text, text
    assert "PICK" not in text


def test_a_feed_path_that_is_a_directory_is_unreadable_not_empty(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])})
    os.makedirs(e.feed)
    code, text = e.cli("pick", "job")
    assert code == 2 and "unreadable" in text


def test_duplicate_host_rows_in_the_feed_are_refused(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord"), row("overlord")])
    code, text = e.cli("pick", "job")
    assert code == 2 and "twice" in text


# ----------------------------------------------------------------------------------- thermal and rest

def thermal_env(tmp_path, other_row, hot_row=None):
    hosts = [H("overlord", 36, mode="local"),
             H("hotbox", 16, ceiling=50, always_on=False, thermal=True, mode="ssh")]
    return Env(tmp_path, hosts, {"job": C(["overlord", "hotbox"])}, [other_row, hot_row or row("hotbox", 0.0)])


def test_thermal_rule_cpu_job_never_goes_to_a_thermal_host_while_another_is_eligible_and_up(tmp_path):
    e = thermal_env(tmp_path, row("overlord", 75.0, threads=36))        # overlord has 1.8 threads free, hotbox 8
    d = json.loads(e.cli("pick", "job", "--json")[1])
    assert d["host"] == "overlord"
    assert any(v["host"] == "hotbox" and v["verdict"] == "held" for v in d["considered"])


def test_thermal_host_is_used_when_nothing_else_is_up(tmp_path):    # positive control for the rule above
    e = thermal_env(tmp_path, row("overlord", 10.0, state="unknown"))
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "hotbox"


def test_a_full_host_still_shields_the_thermal_host(tmp_path):
    e = thermal_env(tmp_path, row("overlord", 99.0, threads=36))        # up, eligible, no room
    code, text = e.cli("pick", "job")
    assert code == 3 and "full" in text and "hotbox" in text           # the job waits; it does not heat the laptop


def test_thermal_rule_does_not_apply_to_a_gpu_class(tmp_path):
    hosts = [H("overlord", 36, mode="local"),
             H("hotbox", 16, ceiling=50, always_on=False, thermal=True, mode="ssh", gpu=["cuda"])]
    e = Env(tmp_path, hosts, {"job": C(["overlord", "hotbox"], kind="gpu", needs={"threads": 1, "gpu": ["cuda"]})},
            [row("overlord", 10.0, threads=36), row("hotbox", 0.0)])
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "hotbox"   # only it has CUDA, so it is the one


def test_class_that_needs_always_on_skips_a_host_that_is_not(tmp_path):
    hosts = [H("overlord", 36, mode="local"), H("sometimes", 64, always_on=False, mode="ssh")]
    e = Env(tmp_path, hosts, {"job": C(["overlord", "sometimes"], requires_always_on=True)},
            [row("overlord", 60.0, threads=36), row("sometimes", 0.0, threads=64)])
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "overlord"
    e.classes = write(tmp_path / "classes2.json", {"schema": "jobclasses-1", "classes": {"job": C(["overlord", "sometimes"])}})
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "sometimes"      # positive control


def test_most_free_threads_wins_then_always_on_then_registry_order(tmp_path):
    hosts = [H("a", 10, mode="ssh"), H("b", 10, mode="ssh"), H("c", 10, always_on=False, mode="ssh")]
    e = Env(tmp_path, hosts, {"job": C(["a", "b", "c"])}, [row("a", 50.0), row("b", 50.0), row("c", 50.0)])
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "a"
    e.set_feed([row("a", 50.0), row("b", 20.0), row("c", 50.0)])
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "b"
    hosts = [H("c", 10, always_on=False, mode="ssh"), H("a", 10, mode="ssh")]
    e = Env(tmp_path, hosts, {"job": C(["a", "c"])}, [row("a", 30.0), row("c", 30.0)])
    assert json.loads(e.cli("pick", "job", "--json")[1])["host"] == "a"


def test_memory_bound_and_ram_short_hosts_are_full(tmp_path):
    bound = row("fakebox", 1.0, memory_bound=True)
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), bound])
    assert e.cli("pick", "job")[0] == 3
    e.set_feed([row("overlord"), row("fakebox", 1.0)])
    assert e.cli("pick", "job")[0] == 0
    e.classes = write(tmp_path / "classes2.json", {"schema": "jobclasses-1", "classes": {"job": C(
        ["fakebox"], needs={"threads": 1, "ram_gb": 20})}})
    e.set_feed([row("overlord"), row("fakebox", 1.0, ram=90.0)])        # 62 GB x 10% free = 6.2 GB
    code, text = e.cli("pick", "job")
    assert code == 3 and "RAM free" in text


def test_a_class_needing_more_threads_than_are_free_waits(tmp_path):
    e = Env(tmp_path, [H("small", 4, mode="ssh")], {"job": C(["small"], needs={"threads": 3})}, [row("small", 50.0)])
    assert e.cli("pick", "job")[0] == 3                                 # 4 x (80-50)% = 1.2 threads
    e.set_feed([row("small", 0.0)])
    assert e.cli("pick", "job")[0] == 0                                 # 3.2 threads


def test_a_closed_host_is_never_a_satisfied_dependency_even_if_the_feed_shows_it_up(tmp_path):
    classes = {"job": C(["overlord"], requires_up=["pve-od"])}
    feed = [row("overlord", threads=36), row("pve-od", 1.0)]
    closed = Env(tmp_path, [H("overlord", 36, mode="local"), H("pve-od", 16, in_cluster=False, accepts=False)], classes, feed)
    code, text = closed.cli("pick", "job")
    assert code == 3 and "dependency" in text and "not in the cluster" in text
    (tmp_path / "joined").mkdir()                                        # positive control: same feed, host in the cluster
    joined = Env(tmp_path / "joined", [H("overlord", 36, mode="local"), H("pve-od", 16)], classes, feed)
    assert joined.cli("pick", "job")[0] == 0


def test_requires_up_defers_the_job_when_the_source_is_unknown(tmp_path):
    hosts = [H("overlord", 36, mode="local"), H("source", 16, always_on=False)]
    e = Env(tmp_path, hosts, {"job": C(["overlord"], requires_up=["source"])}, [row("overlord"), row("source", state="unknown")])
    code, text = e.cli("pick", "job")
    assert code == 3 and "dependency" in text
    e.set_feed([row("overlord"), row("source")])
    assert e.cli("pick", "job")[0] == 0


# -------------------------------------------------------------------- where a job can really be started

def test_an_ssh_host_that_is_not_enabled_is_never_picked_and_nothing_connects(tmp_path, no_ssh):
    e = Env(tmp_path, two_hosts(enabled=False), {"job": C(["fakebox"])}, [row("overlord"), row("fakebox", 0.0)])
    code, text = e.cli("pick", "job")
    assert code == 3 and "not enabled" in text and "owner step" in text
    assert e.cli("pick", "job", "--policy-only")[0] == 0               # policy alone would take it
    assert no_ssh == []


def test_a_local_host_is_runnable_only_when_the_router_is_on_it(tmp_path):
    hosts = [H("overlord", 36, mode="local"), H("other", 8, mode="local")]
    e = Env(tmp_path, hosts, {"job": C(["overlord"])}, [row("overlord", threads=36), row("other", threads=8)])
    assert e.cli("pick", "job", here="overlord")[0] == 0
    code, text = e.cli("pick", "job", here="other")
    assert code == 3 and "the router runs on other, not overlord" in text
    code, text = e.cli("pick", "job", here="no-such-host")
    assert code == 3 and "cannot tell which host it is running on" in text


def test_here_is_found_from_the_hostname_list(tmp_path):
    hosts, _ = r.load_registry(HOSTS_JSON)
    assert r.detect_here(hosts, "OVERLORD") == "overlord"
    assert r.detect_here(hosts, "no-such-machine") is None


def test_ssh_command_is_quoted_for_a_posix_shell():
    cmd = r.ssh_argv("pve-ng", ["/bin/echo", "a b", "$(rm -rf /)"])
    assert cmd[:4] == ["ssh", "-o", "BatchMode=yes", "-o"] and cmd[-3] == "pve-ng" and cmd[-2] == "--"
    assert cmd[-1] == "/bin/echo 'a b' '$(rm -rf /)'"


# --------------------------------------------------------------- registry and class files are strict

def _bad_registry(tmp_path, mutate):
    host = H("overlord", 36, mode="local")
    mutate(host)
    return write(tmp_path / "h.json", {"schema": "jobrouter-hosts-1", "hosts": [host]})


@pytest.mark.parametrize("mutate,needle", [
    (lambda h: h.pop("thermal_limited"), "missing thermal_limited"),
    (lambda h: h.pop("always_on"), "missing always_on"),
    (lambda h: h.update(thermal_limitd=True), "unknown field(s) thermal_limitd"),
    (lambda h: h.update(thermal_limited="yes"), "must be true or false"),
    (lambda h: h.update(ceiling_cpu_pct=0), "ceiling_cpu_pct"),
    (lambda h: h.update(threads=None), "no thread count"),
    (lambda h: h.update(exec={"mode": "rsh"}), "exec.mode"),
    (lambda h: h.update(exec={"mode": "ssh", "alias": "a b"}), "ssh config alias"),
])
def test_registry_refuses_a_missing_misspelled_or_ambiguous_flag(tmp_path, mutate, needle):
    with pytest.raises(r.RegistryError) as e:
        r.load_registry(_bad_registry(tmp_path, mutate))
    assert needle in str(e.value)


def test_registry_refuses_duplicate_ids_and_classes_naming_unknown_hosts(tmp_path):
    h = H("overlord", 36, mode="local")
    with pytest.raises(r.RegistryError, match="twice"):
        r.load_registry(write(tmp_path / "h.json", {"schema": "jobrouter-hosts-1", "hosts": [h, h]}))
    hosts, _ = r.load_registry(write(tmp_path / "h2.json", {"schema": "jobrouter-hosts-1", "hosts": [h]}))
    for bad, needle in [({"job": C(["ghost"])}, "not in the registry"), ({"job": C([])}, "no list means no host"),
                        ({"job": C(["overlord"], argv=[])}, "argv"), ({"Job": C(["overlord"])}, "lowercase"),
                        ({"job": C(["overlord"], timeout_s=0)}, "timeout_s"),
                        ({"job": C(["overlord"], requires_up=["ghost"])}, "not in the registry"),
                        ({"job": C(["overlord"], shell=True)}, "unknown field")]:
        with pytest.raises(r.RegistryError, match=needle):
            r.load_classes(write(tmp_path / "c.json", {"schema": "jobclasses-1", "classes": bad}), hosts)


def test_the_shipped_registry_has_no_ssh_host_enabled_and_closes_the_two_office_boxes():
    hosts, stale = r.load_registry(HOSTS_JSON)
    by = {h.id: h for h in hosts}
    assert stale == 360
    assert not any(h.ssh_enabled for h in hosts)                        # enabling one is the owner's step
    assert not by["pve-od"].in_cluster and not by["pve-r610"].in_cluster
    assert by["GREYWOLF"].thermal_limited and by["GREYWOLF"].ceiling_cpu_pct == 50
    classes = r.load_classes(CLASSES_JSON, hosts)
    assert classes[REAL_CLASS].eligible_hosts == ("overlord",)


# --------------------------------------------------------------------------- invariants under noise

def test_picked_host_is_always_fresh_up_and_shielded_from_thermal_in_random_feeds(tmp_path):
    rng = random.Random(1124)
    hosts = [H("overlord", 36, mode="local"), H("b", 16, mode="ssh"), H("c", 24, mode="ssh"),
             H("hot", 16, ceiling=50, thermal=True, always_on=False, mode="ssh")]
    e = Env(tmp_path, hosts, {"job": C(["overlord", "b", "c", "hot"])})
    reg, stale = r.load_registry(e.hosts)
    cls = r.load_classes(e.classes, reg)["job"]
    picks = Counter()
    for _ in range(400):
        rows = []
        for h in hosts:
            if rng.random() < 0.1:
                continue                                                # missing from the feed
            rows.append(row(h["id"], rng.choice([0.0, 20.0, 50.0, 85.0, 100.0]), age=rng.choice([10, 200, 359, 361, 900]),
                            threads=h["threads"], state=rng.choice(["up", "up", "up", "unknown", "off"])))
        e.set_feed(rows, file_age=rng.choice([0, 100, 400]))
        feed = r.read_feed(e.feed, NOW)
        dec = r.pick(cls, reg, feed, NOW, stale, r.make_runnable("overlord"))
        if dec.outcome != "placed":
            continue
        picks[dec.host.id] += 1
        st = r.classify(dec.host, feed, NOW, stale)
        assert st.state == r.UP and st.age_s <= 360
        assert dec.free_threads >= 1
        if dec.host.thermal_limited:
            for other in reg:
                if not other.thermal_limited and other.id in ("overlord", "b", "c"):
                    o = r.classify(other, feed, NOW, stale)
                    assert o.state != r.UP, "thermal host picked while %s was up" % other.id
    assert len(picks) >= 3                                              # the generator really exercises several hosts


# ----------------------------------------------------------------------- queue, dispatch and the log

def test_a_job_runs_for_real_on_the_picked_host_and_the_log_says_where(tmp_path):
    e = Env(tmp_path, [H("overlord", 36, mode="local")], {"job": C(["overlord"])}, [row("overlord", threads=36)])
    assert e.cli("submit", "job")[0] == 0
    code, text = e.cli("dispatch")
    assert code == 0 and "RAN" in text and "on overlord: ok" in text, text
    log = e.log()                                                       # read as a stranger would
    assert [x["event"] for x in log] == ["submitted", "placed", "finished"]
    placed, fin = log[1], log[2]
    assert placed["host"] == "overlord" and placed["class"] == "job" and placed["considered"]
    assert fin["status"] == "ok" and fin["exit_code"] == 0 and fin["host"] == "overlord"
    done = [n for n in os.listdir(os.path.join(e.state, "queue", "done"))]
    assert len(done) == 1
    rec = json.load(open(os.path.join(e.state, "queue", "done", done[0]), encoding="utf-8"))
    assert rec["result"]["stdout_tail"].strip() == "ran" and rec["placement"]["host"] == "overlord"
    assert os.listdir(os.path.join(e.state, "queue", "pending")) == []
    assert os.listdir(os.path.join(e.state, "queue", "running")) == []
    code, text = e.cli("status")
    assert "pending 0, running 0, done 1" in text and "finished job overlord" in text


def test_fake_second_machine_takes_the_job_when_it_is_the_better_host(tmp_path, no_ssh):
    fake = FakeMachines()
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord", "fakebox"])},
            [row("overlord", 70.0, threads=36), row("fakebox", 2.0, threads=24)])
    assert e.cli("run", "job", runner=fake)[0] == 0
    assert fake.runs and fake.runs[0][0] == "fakebox"
    assert [x["host"] for x in e.log() if x["event"] in ("placed", "finished")] == ["fakebox", "fakebox"]
    assert no_ssh == []                                                 # the fake runner stood in for ssh


def test_fake_second_machine_with_a_stale_reading_gets_nothing(tmp_path, no_ssh):
    fake = FakeMachines()
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord", "fakebox"])},
            [row("overlord", 70.0, threads=36), row("fakebox", 2.0, age=400, threads=24)])
    assert e.cli("run", "job", runner=fake)[0] == 0
    assert [h for h, _ in fake.runs] == ["overlord"]
    (tmp_path / "again").mkdir()
    e2 = Env(tmp_path / "again", two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), row("fakebox", 2.0, age=400)])
    code, text = e2.cli("run", "job", runner=fake)
    assert code == 3 and "DEFERRED" in text and [h for h, _ in fake.runs] == ["overlord"]   # nothing new ran


def test_a_deferred_job_stays_queued_and_logs_each_reason_once(tmp_path):
    fake = FakeMachines()
    e = Env(tmp_path, two_hosts(), {"job": C(["fakebox"])}, [row("overlord"), row("fakebox", state="unknown")])
    assert e.cli("run", "job", runner=fake)[0] == 3
    assert e.cli("dispatch", runner=fake)[0] == 3
    assert e.cli("dispatch", runner=fake)[0] == 3
    assert [x["event"] for x in e.log()] == ["submitted", "deferred"]  # three ticks, one line
    assert fake.runs == []
    assert len(os.listdir(os.path.join(e.state, "queue", "pending"))) == 1
    e.set_feed([row("overlord"), row("fakebox")])                       # the host comes back: same job now runs
    assert e.cli("dispatch", runner=fake)[0] == 0 and fake.runs[0][0] == "fakebox"


def test_a_missing_feed_during_dispatch_stops_the_job_and_runs_nothing(tmp_path):
    fake = FakeMachines()
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])})
    assert e.cli("submit", "job", runner=fake)[0] == 0
    code, text = e.cli("dispatch", runner=fake)
    assert code == 2 and "not found" in text and fake.runs == []
    assert len(os.listdir(os.path.join(e.state, "queue", "pending"))) == 1
    assert e.log()[-1]["event"] == "deferred" and e.log()[-1]["kind"] == "feed"


def test_no_log_no_run(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord", threads=36)])
    assert e.cli("submit", "job")[0] == 0
    os.remove(os.path.join(e.state, "placements.jsonl"))
    os.makedirs(os.path.join(e.state, "placements.jsonl"))              # a directory where the log should be
    fake = FakeMachines()
    code, text = e.cli("dispatch", runner=fake)
    assert code == 2 and "cannot write the placement log" in text and fake.runs == []
    assert len(os.listdir(os.path.join(e.state, "queue", "pending"))) == 1      # put back, not lost
    assert os.listdir(os.path.join(e.state, "queue", "running")) == []


def test_one_job_of_a_class_at_a_time_when_dedupe_is_on(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"]), "free": C(["overlord"], dedupe=False)},
            [row("overlord", threads=36)])
    assert e.cli("submit", "job")[0] == 0
    code, text = e.cli("submit", "job")
    assert code == 0 and text.startswith("NOT SUBMITTED") and "already pending" in text
    assert len(os.listdir(os.path.join(e.state, "queue", "pending"))) == 1
    assert e.cli("submit", "free")[0] == 0 and e.cli("submit", "free")[0] == 0   # positive control
    assert e.cli("submit", "nope")[0] == 2


def test_failed_and_timed_out_jobs_are_recorded_and_the_exit_code_says_so(tmp_path):
    fail = C(["overlord"], argv=[sys.executable, "-c", "import sys; print('boom'); sys.exit(7)"])
    slow = C(["overlord"], argv=[sys.executable, "-c", "import time; time.sleep(20)"], timeout_s=1)
    missing = C(["overlord"], argv=["/definitely/not/a/program"])
    e = Env(tmp_path, [H("overlord", 36, mode="local")], {"fail": fail, "slow": slow, "missing": missing},
            [row("overlord", threads=36)])
    for name, want in (("fail", "failed"), ("slow", "timeout"), ("missing", "error")):
        code, text = e.cli("run", name)
        assert code == 1 and want in text, (name, text)
    results = {x["class"]: x["status"] for x in e.log() if x["event"] == "finished"}
    assert results == {"fail": "failed", "slow": "timeout", "missing": "error"}


def test_a_second_dispatcher_is_refused_while_the_first_holds_the_lock(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord", threads=36)])
    assert e.cli("submit", "job")[0] == 0
    d = r.ensure_state(e.state)
    with r.dispatch_lock(d["lock"]):
        code, text = e.cli("dispatch")
        assert code == 4 and text.startswith("LOCKED")
    assert e.cli("dispatch", runner=FakeMachines())[0] == 0             # lock released: now it runs


def test_a_running_job_with_no_router_is_shown_overdue_and_never_re_run(tmp_path):
    fake = FakeMachines()
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"], timeout_s=60)}, [row("overlord", threads=36)])
    d = r.ensure_state(e.state)
    stuck = {"schema": "job-1", "id": "20261121T000000Z-job-aaaaaa", "class": "job", "submitted_at": "2026-11-21T00:00:00Z"}
    write(os.path.join(d["running"], stuck["id"] + ".json"), stuck)
    code, text = e.cli("status", "--json")
    st = json.loads(text)
    assert st["running"][0]["overdue"] and "not re-run" in st["running"][0]["overdue"]
    assert e.cli("dispatch", runner=fake)[0] == 0 and fake.runs == []
    assert len(os.listdir(d["running"])) == 1


def test_the_log_command_prints_what_a_stranger_can_parse(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord", threads=36)])
    e.cli("run", "job", runner=FakeMachines())
    code, text = e.cli("log", "--last", "2")
    lines = [json.loads(x) for x in text.splitlines()]
    assert code == 0 and [x["event"] for x in lines] == ["placed", "finished"]


def test_pick_json_and_unknown_class(tmp_path):
    e = Env(tmp_path, two_hosts(), {"job": C(["overlord"])}, [row("overlord", threads=36)])
    d = json.loads(e.cli("pick", "job", "--json")[1])
    assert d["host"] == "overlord" and d["here"] == "overlord" and d["outcome"] == "placed"
    code, text = e.cli("pick", "nope")
    assert code == 2 and "unknown job class" in text


# ------------------------------------------------------------------------------- Law 9, by reading it

def test_the_router_imports_nothing_that_can_reach_a_network_and_only_runs_processes_in_one_place():
    tree = ast.parse(open(_PATH, encoding="utf-8").read())
    allowed = {"argparse", "contextlib", "datetime", "json", "os", "re", "secrets", "shlex", "socket", "subprocess",
               "sys", "time", "collections", "msvcrt", "fcntl"}
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    assert imported <= allowed, imported - allowed
    socket_uses = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                   and isinstance(n.value, ast.Name) and n.value.id == "socket"}
    assert socket_uses == {"gethostname"}                               # the machine's own name, nothing else
    callers = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for c in ast.walk(fn):
            if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in ("run", "Popen", "call", "check_output")
                    and isinstance(c.func.value, ast.Name) and c.func.value.id == "subprocess"):
                callers.add(fn.name)
    assert callers == {"run_local"}                                     # ssh_argv only builds a command line
