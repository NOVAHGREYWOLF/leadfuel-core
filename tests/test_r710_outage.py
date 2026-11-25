"""NODE p16-3: the outage explainer says EXPLAINED only on the 710's own record, WINDOW when only
overlord's journal speaks, UNKNOWN when it saw nothing; the collection plan is reads only; the retry
wrapper is off by default, never retries a job that ran, and its give-up line parses in the morning proof.

All log text is synthetic. Nothing connects to a machine; probe, sleep and run are replaced.
"""
import datetime as dt
import importlib.util
import os

import pytest

_HERE = os.path.dirname(__file__)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, os.pardir, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ox = _load("outage_explainer", "node/outage_explainer.py")
rw = _load("retry_when_unreachable", "node/retry_when_unreachable.py")
mp = _load("morning_proof", "watch/morning_proof.py")

OFF = "Nov {d} {t} overlord pvestatd[900]: storage 'r710-backup' is not online"
JOURNAL = "\n".join([
    OFF.format(d=20, t="15:33:54"),
    OFF.format(d=20, t="15:34:04"),
    OFF.format(d=21, t="13:08:22"),
    "Nov 21 13:09:03 overlord kernel: nfsrahead: /mnt/pve/r710-backup readahead",
])


def test_window_from_journal_alone_does_not_name_a_cause():
    rep = ox.explain(JOURNAL, None, 2026)
    assert rep["verdict"] == "WINDOW" and rep["cause"] is None
    assert rep["window"]["start_seen"].startswith("2026-11-20T15:33:54")
    assert rep["window"]["recovered_line_seen"] is True
    assert 21 < rep["window"]["hours"] < 22
    assert "UNKNOWN" in rep["reason"]


def test_cause_named_only_from_the_710s_own_record_inside_the_window():
    sel = "Nov 20 15:20:11 r710 sel: AC power lost\nNov 21 13:05:00 r710 sel: AC power restored"
    rep = ox.explain(JOURNAL, sel, 2026)
    assert rep["verdict"] == "EXPLAINED" and rep["cause"] == "ac_power_loss"


def test_event_outside_window_is_not_a_cause():
    sel = "Oct 02 03:00:00 r710 sel: AC power lost"
    rep = ox.explain(JOURNAL, sel, 2026)
    assert rep["verdict"] == "WINDOW" and rep["cause"] is None


def test_boot_only_is_not_a_cause():
    rep = ox.explain(JOURNAL, "Nov 21 13:00:00 r710 sel: system boot", 2026)
    assert rep["verdict"] == "WINDOW" and rep["cause"] is None


@pytest.mark.parametrize("text", [None, "", "no storage lines here\n"])
def test_nothing_seen_is_unknown_never_no_outage(text):
    assert ox.explain(text, None, 2026)["verdict"] == "UNKNOWN"


def test_short_format_without_year_cannot_be_dated_and_says_so():
    rep = ox.explain(JOURNAL, None, None)
    assert rep["verdict"] == "UNKNOWN"
    assert any("--year" in r for r in rep["read"])


def test_iso_lines_carry_their_own_year():
    iso = "2026-11-20T15:33:54-0800 overlord pvestatd[1]: storage 'r710-backup' is not online"
    assert ox.explain(iso, None, None)["verdict"] == "WINDOW"


def test_plan_is_reads_only():
    cmds = ox.plan()
    assert cmds and all(c["command"].split()[0] in ox._READ_VERBS for c in cmds)


@pytest.mark.parametrize("bad", ["rm -rf /x", "ipmitool chassis power cycle", "racadm serveraction powerup",
                                 "tail -n 5 f > g", "journalctl; reboot", "ipmitool", "qm stop 103"])
def test_assert_read_only_refuses_writes(bad):
    with pytest.raises(ValueError):
        ox.assert_read_only(bad)


# ---- retry wrapper ----

def _run(job="vault-sync", probes=(), enabled=True, tries=3, tmp=None, rc=0):
    seq, slept, ran = list(probes), [], []
    sf = os.path.join(str(tmp), "s.status")
    code = rw.run(job, ["do", "it"], sf, tries=tries, wait=600, enabled=enabled,
                  probe_fn=lambda h, p: seq.pop(0), sleep_fn=slept.append,
                  run_fn=lambda c: ran.append(c) or rc,
                  now_fn=lambda: dt.datetime(2026, 11, 22, 10, 45, tzinfo=dt.timezone.utc))
    return code, slept, ran, sf


def test_off_by_default_runs_once_without_probing(tmp_path):
    code, slept, ran, sf = _run(probes=[], enabled=False, tmp=tmp_path, rc=7)
    assert code == 7 and ran == [["do", "it"]] and slept == [] and not os.path.exists(sf)


def test_reachable_first_probe_runs_once(tmp_path):
    code, slept, ran, _ = _run(probes=[True], tmp=tmp_path)
    assert code == 0 and len(ran) == 1 and slept == []


def test_comes_back_on_second_probe_then_runs(tmp_path):
    code, slept, ran, _ = _run(probes=[False, True], tmp=tmp_path)
    assert code == 0 and len(ran) == 1 and slept == [600]


def test_a_job_that_ran_and_failed_is_not_retried(tmp_path):
    code, slept, ran, _ = _run(probes=[True], tmp=tmp_path, rc=2)
    assert code == 2 and len(ran) == 1


def test_never_back_does_not_run_and_writes_one_line(tmp_path):
    code, slept, ran, sf = _run(probes=[False, False, False], tmp=tmp_path)
    assert code == rw.EXIT_UNREACHABLE and ran == [] and slept == [600, 600]
    text = open(sf).read().splitlines()
    assert text == ["20261122T104500Z UNKNOWN WHY: 710 unreachable after 3 probes over 20 min"]


@pytest.mark.parametrize("job,state", [("vault-sync", "unknown"), ("greywolf-state", "fail")])
def test_give_up_line_parses_in_the_morning_proof(tmp_path, job, state):
    _, _, _, sf = _run(job=job, probes=[False] * 3, tmp=tmp_path)
    parse = mp.parse_vault_sync if job == "vault-sync" else mp.parse_greywolf
    got = parse(open(sf).read())
    assert [r.state for r in got] == [state], got


def test_probe_error_is_not_reachable():
    assert rw.probe("127.0.0.1", 1, timeout=0.2) is False
