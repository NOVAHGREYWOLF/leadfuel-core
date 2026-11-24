"""NODE desks-3-6: the CPU attribution names a process only from counters it read, calls a leaked
scan only on the stated rule, says UNKNOWN when it cannot read, and never prints a command line or
stops anything.

Every process, pid and command here is synthetic. Nothing reads the real machine: the process
list, netstat, the machine's busy counters and the clock are all replaced by the test.
"""
import importlib.util
import io
import json
import os

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "node", "cpu_who.py")
_spec = importlib.util.spec_from_file_location("cpu_who", _PATH)
cw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cw)

NOW = 1_800_000_000
GNU_FIND = r"C:\Program Files\Git\usr\bin\find.exe"
WIN_FIND = r"C:\Windows\System32\find.exe"
SECRET = "tok_SYNTHETIC_0123456789"


def P(pid, name="x.exe", ppid=1, exe=None, cmd=None, created=NOW - 10_000, cpu=0.0):
    return cw.Proc(pid, ppid, name, exe, cmd, created, cpu)


def find(pid, cmd, age_min=60, exe=GNU_FIND, ppid=1):
    return P(pid, "find.exe", ppid, exe, cmd, NOW - age_min * 60, 100.0)


# ---------------------------------------------------------------- parse_snapshot

def row(pid, name="a.exe", kernel=10_000_000, user=20_000_000, **kw):
    d = {"pid": pid, "ppid": 1, "name": name, "exe": None, "cmd": None, "created": NOW - 100,
         "kernel": kernel, "user": user}
    d.update(kw)
    return d


def test_parse_reads_a_list_and_converts_100ns_units_to_seconds():
    procs, bad = cw.parse_snapshot(json.dumps([row(7, kernel=10_000_000, user=20_000_000)]))
    assert bad == 0 and procs[0].cpu_s == 3.0 and procs[0].pid == 7


def test_parse_reads_one_bare_object():
    procs, _ = cw.parse_snapshot(json.dumps(row(7)))
    assert [p.pid for p in procs] == [7]


def test_parse_counts_a_row_without_a_pid_or_name_as_bad_not_silently_dropped():
    procs, bad = cw.parse_snapshot(json.dumps([row(1), {"name": "x"}, {"pid": 3}, 5]))
    assert len(procs) == 1 and bad == 3


def test_missing_cpu_counters_are_none_never_zero():
    procs, _ = cw.parse_snapshot(json.dumps([row(1, kernel=None), row(2, user=None)]))
    assert [p.cpu_s for p in procs] == [None, None]


@pytest.mark.parametrize("text", ["", "not json", '"a string"', "3"])
def test_unreadable_snapshot_raises_value_error(text):
    with pytest.raises(ValueError):
        cw.parse_snapshot(text)


# ---------------------------------------------------------------- attribute

def test_a_share_is_cpu_seconds_over_interval_over_cpus():
    before = [P(1, "a.exe", cpu=10.0), P(2, "a.exe", cpu=10.0)]
    after = [P(1, "a.exe", cpu=12.0), P(2, "a.exe", cpu=12.0)]
    att = cw.attribute(before, after, interval_s=10, ncpu=4)
    assert len(att.rows) == 1
    assert att.rows[0].pct == pytest.approx(10.0) and att.rows[0].procs == 2    # 4 cpu-s / (10 s * 4)
    assert att.explained_pct == pytest.approx(10.0)


def test_rows_are_sorted_biggest_first():
    before = [P(1, "small.exe", cpu=0), P(2, "big.exe", cpu=0)]
    after = [P(1, "small.exe", cpu=1), P(2, "big.exe", cpu=9)]
    assert [r.name for r in cw.attribute(before, after, 10, 1).rows] == ["big.exe", "small.exe"]


def test_a_process_started_inside_the_interval_counts_all_its_cpu_and_is_tallied():
    att = cw.attribute([], [P(5, "new.exe", cpu=4.0)], 10, 2)
    assert att.rows[0].pct == pytest.approx(20.0) and att.started == 1 and att.exited == 0


def test_a_process_that_exited_cannot_be_counted_and_is_only_tallied():
    att = cw.attribute([P(5, "gone.exe", cpu=99.0)], [], 10, 2)
    assert att.rows == [] and att.exited == 1


def test_a_reused_pid_is_a_different_process_not_a_huge_negative_or_positive_delta():
    before = [P(5, "old.exe", created=NOW - 500, cpu=900.0)]
    after = [P(5, "new.exe", created=NOW - 3, cpu=1.0)]
    att = cw.attribute(before, after, 10, 1)
    assert [r.name for r in att.rows] == ["new.exe"] and att.exited == 1 and att.started == 1


def test_a_counter_that_went_backwards_or_is_missing_is_not_counted_and_is_reported():
    before = [P(1, "a.exe", cpu=10.0), P(2, "b.exe", cpu=None), P(3, "c.exe", cpu=5.0)]
    after = [P(1, "a.exe", cpu=9.0), P(2, "b.exe", cpu=5.0), P(3, "c.exe", cpu=None)]
    att = cw.attribute(before, after, 10, 1)
    assert att.rows == [] and att.no_cpu == 3


@pytest.mark.parametrize("interval,ncpu", [(0, 4), (-1, 4), (10, 0)])
def test_a_share_without_an_interval_or_cpu_count_is_refused(interval, ncpu):
    with pytest.raises(ValueError):
        cw.attribute([], [], interval, ncpu)


# ---------------------------------------------------------------- verdict and the machine's busy figure

@pytest.mark.parametrize("busy,interval,want", [
    (100.0, 10, cw.SATURATED), (90.0, 10, cw.SATURATED), (89.9, 10, cw.BUSY), (60.0, 10, cw.BUSY),
    (59.9, 10, cw.QUIET), (0.0, 10, cw.QUIET),
    (None, 10, cw.UNKNOWN), (100.0, 0.5, cw.UNKNOWN),
])
def test_verdict(busy, interval, want):
    assert cw.verdict(busy, interval) == want


def test_machine_busy_is_one_minus_idle_over_kernel_plus_user():
    t0, t1 = (0, 0, 0), (250, 800, 200)        # kernel includes idle: total = 1000, idle = 250
    assert cw.machine_busy_pct(t0, t1) == pytest.approx(75.0)


@pytest.mark.parametrize("t0,t1", [(None, (1, 2, 3)), ((1, 2, 3), None), ((5, 5, 5), (5, 5, 5))])
def test_machine_busy_is_none_when_it_cannot_be_read(t0, t1):
    assert cw.machine_busy_pct(t0, t1) is None


def test_machine_busy_is_clamped():
    assert cw.machine_busy_pct((0, 0, 0), (-50, 100, 0)) == 100.0


# ---------------------------------------------------------------- command lines and roots

def test_tokenize_keeps_backslashes_and_unquotes():
    assert cw.tokenize(r'"C:\Program Files\Git\usr\bin\find.exe" / -iname "a b"') == \
        [r"C:\Program Files\Git\usr\bin\find.exe", "/", "-iname", "a b"]
    assert cw.tokenize("") == [] and cw.tokenize(None) == []
    assert cw.tokenize('find "" x') == ["find", "", "x"]


@pytest.mark.parametrize("cmd,roots", [
    ("find / -iname x", ["/"]),
    (r'"C:\Program Files\Git\usr\bin\find.exe" / -name x', ["/"]),
    ("find -name x", []),
    ("find -L / -name x", ["/"]),
    ("find . -name /", ["."]),
    ("find /tmp / -name x", ["/tmp", "/"]),
    ("find C:\\ -name x", ["C:\\"]),
    ("find ( -name x )", []),
    ("find ! -name x", []),
    ("", []),
    (None, []),
])
def test_search_roots(cmd, roots):
    assert cw.search_roots(cmd) == roots


@pytest.mark.parametrize("path,want", [
    ("/", True), ("//", True), ("C:\\", True), ("f:/", True), ("D:\\\\", True),
    ("C:", False), (".", False), ("/tmp", False), ("C:\\Users", False), ("/c", False), ("", False),
])
def test_is_root(path, want):
    assert cw.is_root(path) == want


# ---------------------------------------------------------------- leaked scans

def test_an_old_find_from_slash_is_a_leak_and_a_young_one_is_not():
    old, young = find(1, "find / -iname x", age_min=131), find(2, "find / -iname x", age_min=29)
    leaks, amb, unread = cw.find_leaks([old, young], NOW)
    assert [p.pid for p in leaks] == [1] and amb == [] and unread == []


def test_the_age_threshold_is_inclusive_and_configurable():
    p = find(1, "find / -iname x", age_min=30)
    assert cw.find_leaks([p], NOW)[0] == [p]
    assert cw.find_leaks([p], NOW, min_age_min=31)[0] == []


def test_a_search_of_a_project_folder_is_not_a_leak_however_old():
    assert cw.find_leaks([find(1, "find /f/work -name x", age_min=900)], NOW)[0] == []


def test_a_drive_root_is_a_leak():
    assert cw.find_leaks([find(1, "find F:\\ -name x")], NOW)[0]


def test_the_windows_text_filter_is_never_a_leak_even_with_slash_switches():
    p = find(1, 'find /i "needle"', age_min=900, exe=WIN_FIND)
    assert cw.find_leaks([p], NOW) == ([], [], [])
    assert cw.find_leaks([find(2, 'find / x', age_min=900, exe=r"C:\WINDOWS\SysWOW64\find.exe")], NOW) == ([], [], [])


def test_an_msys_drive_mount_root_is_a_leak_when_the_exe_is_known_gnu_and_ambiguous_when_not():
    known = find(1, "find /f -name x", exe=GNU_FIND)
    unknown = find(2, "find /i -name x", exe=None)
    leaks, amb, unread = cw.find_leaks([known, unknown], NOW)
    assert [p.pid for p in leaks] == [1] and [p.pid for p in amb] == [2] and unread == []


def test_a_find_whose_command_line_or_start_time_is_unreadable_is_unreadable_not_clean():
    a = P(1, "find.exe", exe=GNU_FIND, cmd=None, created=NOW - 9999)
    b = P(2, "find.exe", exe=GNU_FIND, cmd="find / x", created=None)
    leaks, amb, unread = cw.find_leaks([a, b], NOW)
    assert leaks == [] and amb == [] and [p.pid for p in unread] == [1, 2]


def test_other_processes_and_case_differences():
    other = P(1, "python.exe", exe=GNU_FIND, cmd="find / x", created=NOW - 9999)
    upper = find(2, "find / -name x")._replace(name="FIND.EXE")
    assert [p.pid for p in cw.find_leaks([other, upper], NOW)[0]] == [2]


def test_parent_chain_names_the_session_that_left_it():
    procs = [P(1, "claude.exe", ppid=0, created=NOW - 9000), P(2, "bash.exe", ppid=1, created=NOW - 8000),
             P(3, "find.exe", ppid=2, created=NOW - 7000)]
    assert cw.parent_chain(procs, 3) == ["bash.exe(2)", "claude.exe(1)"]


def test_an_orphan_says_its_parent_is_gone_and_a_reused_parent_pid_counts_as_gone():
    orphan = [P(3, "find.exe", ppid=2, created=NOW - 7000)]
    assert cw.parent_chain(orphan, 3) == ["pid 2 gone"]
    reused = [P(2, "svchost.exe", ppid=0, created=NOW - 10), P(3, "find.exe", ppid=2, created=NOW - 7000)]
    assert cw.parent_chain(reused, 3) == ["pid 2 gone"]


def test_parent_chain_is_bounded_and_survives_a_cycle():
    cyc = [P(1, "a.exe", ppid=2, created=NOW - 5), P(2, "b.exe", ppid=1, created=NOW - 5)]
    assert len(cw.parent_chain(cyc, 1)) <= 4


# ---------------------------------------------------------------- the CPU report

def _world():
    before = [P(10, "claude.exe", cpu=0.0), P(11, "claude.exe", cpu=0.0), P(12, "MsMpEng.exe", cpu=0.0),
              P(13, "bash.exe", ppid=10, cpu=0.0),
              P(20, "find.exe", ppid=13, exe=GNU_FIND, cmd="find / -iname %s" % SECRET, created=NOW - 7860, cpu=3900.0)]
    after = [P(10, "claude.exe", cpu=8.0), P(11, "claude.exe", cpu=8.0), P(12, "MsMpEng.exe", cpu=12.0),
             P(13, "bash.exe", ppid=10, cpu=0.1),
             P(20, "find.exe", ppid=13, exe=GNU_FIND, cmd="find / -iname %s" % SECRET, created=NOW - 7860, cpu=3965.0)]
    return before, after


def test_report_names_the_leak_its_parents_and_the_owner_script_and_never_prints_the_command():
    before, after = _world()
    first, ev = cw.report_cpu(before, after, 10, 16, 100.0, NOW)
    text = "\n".join([first] + ev)
    assert first.startswith("SATURATED machine 100% busy over 10.0 s on 16 logical CPUs")
    assert "LEAKED SCANS: 1" in text and "pid 20" in text and "bash.exe(13) < claude.exe(10)" in text
    assert "Stop-LeakedScans.ps1" in text and "cpu 3965 s" in text and "age 2 h 11 min" in text
    assert SECRET not in text and "-iname" not in text


def test_report_says_how_much_is_not_explained_by_any_process():
    before, after = _world()
    first, ev = cw.report_cpu(before, after, 10, 16, 100.0, NOW)
    explained = float(first.split("explain ")[1].split("%")[0])
    assert 0 < explained < 100
    assert any(l.startswith("not explained by any process: ") for l in ev)


def test_report_without_the_machine_figure_is_unknown_not_quiet():
    before, after = _world()
    first, ev = cw.report_cpu(before, after, 10, 16, None, NOW)
    assert first.startswith("UNKNOWN") and not any(l.startswith("not explained") for l in ev)


def test_report_says_when_no_leak_was_seen_and_groups_the_tail():
    procs = [P(i, "n%d.exe" % i, cpu=0.0) for i in range(15)]
    after = [p._replace(cpu_s=1.0) for p in procs]
    first, ev = cw.report_cpu(procs, after, 10, 16, 5.0, NOW, top=3)
    assert first.startswith("QUIET") and "leaked scans: none seen" in ev
    assert any("(all the others)" in l and "12 name(s)" in l for l in ev)


def test_report_flags_unreadable_and_ambiguous_finds_instead_of_staying_silent():
    after = [find(1, "find /i x", exe=None), P(2, "find.exe", exe=GNU_FIND, cmd=None, created=NOW - 9000)]
    _, ev = cw.report_cpu(after, after, 10, 4, 10.0, NOW)
    text = "\n".join(ev)
    assert "could not be told apart" in text and "UNKNOWN for 1 find.exe" in text


# ---------------------------------------------------------------- connections to a port

NETSTAT = """\
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    127.0.0.1:11434        0.0.0.0:0              LISTENING       500
  TCP    127.0.0.1:50001        127.0.0.1:11434        ESTABLISHED     700
  TCP    127.0.0.1:50002        127.0.0.1:11434        ESTABLISHED     700
  TCP    127.0.0.1:50003        127.0.0.1:11434        ESTABLISHED     701
  TCP    127.0.0.1:11434        127.0.0.1:50001        ESTABLISHED     500
  TCP    127.0.0.1:50009        127.0.0.1:11434        TIME_WAIT       0
  TCP    127.0.0.1:50010        127.0.0.1:11434        TIME_WAIT       0
  TCP    [::1]:50011            [::1]:11434            ESTABLISHED     702
  TCP    127.0.0.1:60000        127.0.0.1:8106         ESTABLISHED     703
"""
PROCS = [P(500, "ollama.exe"), P(700, "window.exe"), P(701, "python.exe"), P(702, "other.exe"), P(703, "x.exe")]


def test_parse_netstat_skips_headers_and_reads_ipv6():
    conns = cw.parse_netstat(NETSTAT)
    assert len(conns) == 9 and conns[0].state == "LISTENING"
    assert any(c.local.startswith("[::1]") for c in conns)


def test_clients_are_the_client_end_only_and_pid_zero_is_anonymous():
    by_owner, anon, listeners = cw.clients_of(cw.parse_netstat(NETSTAT), PROCS, 11434)
    assert by_owner == {"window.exe(700)": 2, "python.exe(701)": 1, "other.exe(702)": 1}
    assert anon == {"TIME_WAIT": 2} and listeners == [500]


def test_report_clients_names_who_and_says_what_it_cannot_see():
    first, ev = cw.report_clients(cw.parse_netstat(NETSTAT), PROCS, 11434)
    assert first.startswith("CLIENTS-SEEN 4 open connection(s) to port 11434 from 3 process(es)")
    text = "\n".join(ev)
    assert "ollama.exe(500)" in text and "window.exe(700)" in text and "no recorded owner" in text


def test_no_listener_is_unknown_and_no_open_client_is_not_clients_seen():
    first, _ = cw.report_clients(cw.parse_netstat(NETSTAT), PROCS, 9999)
    assert first.startswith("UNKNOWN")
    only_listener = "  TCP    127.0.0.1:11434        0.0.0.0:0              LISTENING       500\n"
    first, ev = cw.report_clients(cw.parse_netstat(only_listener), PROCS, 11434)
    assert first.startswith("NO-OPEN-CLIENT")


def test_a_client_pid_missing_from_the_process_list_is_named_as_such():
    by_owner, _, _ = cw.clients_of(cw.parse_netstat(NETSTAT), [P(500, "ollama.exe")], 11434)
    assert "pid-not-in-list(700)" in by_owner


# ---------------------------------------------------------------- Ollama's request rate

def gin(sec, path="/api/tags", method="GET", status=200):
    return '[GIN] 2026/11/23 - 15:%02d:%02d | %d |    1.06s |       127.0.0.1 | %-8s "%s"' % (
        sec // 60, sec % 60, status, method, path)


def test_parse_gin_reads_timestamps_into_seconds_and_counts_bad_lines():
    text = "\n".join([gin(0), gin(2), "[GIN] garbled", "time=2026 level=INFO other log line", gin(5, "/api/ps")])
    entries, bad = cw.parse_gin(text)
    assert [e.t for e in entries] == [0.0, 2.0, 5.0] and bad == 1
    assert entries[2].path == "/api/ps" and entries[0].method == "GET"


def test_a_query_string_is_not_part_of_the_path():
    entries, _ = cw.parse_gin(gin(0, "/api/tags?x=1"))
    assert entries[0].path == "/api/tags"


def test_parse_gin_crosses_midnight():
    a = '[GIN] 2026/11/23 - 23:59:59 | 200 | 1ms | 127.0.0.1 | GET "/api/ps"'
    b = '[GIN] 2026/11/24 - 00:00:01 | 200 | 1ms | 127.0.0.1 | GET "/api/ps"'
    entries, _ = cw.parse_gin(a + "\n" + b)
    assert entries[1].t - entries[0].t == 2.0


def test_polling_dominated_gives_rate_gap_and_says_it_cannot_name_the_client():
    lines = [gin(s) for s in range(0, 120)] + [gin(s, "/api/version") for s in range(0, 120, 2)]
    lines.append(gin(60, "/api/chat", "POST"))
    entries, bad = cw.parse_gin("\n".join(lines))
    entries.sort(key=lambda e: e.t)
    first, ev = cw.report_ollama_rate(entries, bad)
    assert first.startswith("POLLING-DOMINATED 1.") and "1 POST" in first
    text = "\n".join(ev)
    assert "median gap between calls 1.0 s" in text and "median gap between calls 2.0 s" in text
    assert "no client address or user agent" in text


def test_mostly_inference_is_mixed():
    lines = [gin(s, "/api/chat", "POST") for s in range(0, 60)]
    entries, _ = cw.parse_gin("\n".join(lines))
    assert cw.report_ollama_rate(entries)[0].startswith("MIXED")


@pytest.mark.parametrize("n,span", [(5, 100), (30, 2)])
def test_too_little_log_is_unknown(n, span):
    entries, _ = cw.parse_gin("\n".join(gin(int(i * span / n)) for i in range(n)))
    assert cw.report_ollama_rate(entries)[0].startswith("UNKNOWN")


def test_read_tail_text_drops_the_cut_line(tmp_path):
    p = tmp_path / "o.log"
    p.write_text("\n".join(gin(i % 60) for i in range(500)) + "\n")
    text = cw.read_tail_text(str(p), window=1000)
    assert text.startswith("[GIN]") and len(text) <= 1000


# ---------------------------------------------------------------- main, with every reading faked

def fake_main(argv, snapshots, netstat="", times=((0, 0, 0), (0, 1000, 0)), ncpu=16, log=None, own=None):
    snaps = iter(snapshots)
    clock = {"t": 0.0}
    out = io.StringIO()
    tick = iter(times)

    def mono():
        return clock["t"]

    def sleep(s):
        clock["t"] += s
        sleep.called = s
    sleep.called = None
    rc = cw.main(argv, out=out, clock=lambda: NOW, mono=mono, sleep=sleep,
                 snapshot_fn=lambda: next(snaps), netstat_fn=lambda: netstat,
                 times_fn=lambda: next(tick), ncpu_fn=lambda: ncpu)
    return rc, out.getvalue(), sleep.called


def snap(*rows):
    return json.dumps(list(rows))


def test_main_samples_twice_sleeps_the_requested_seconds_and_prints_the_verdict_first():
    a = snap(row(10, "claude.exe", kernel=0, user=0))
    b = snap(row(10, "claude.exe", kernel=0, user=1_600_000_000))     # 160 cpu-s over 10 s on 16 cpus = 100%
    rc, text, slept = fake_main(["--seconds", "10"], [a, b], times=((0, 0, 0), (0, 1000, 0)))
    lines = text.splitlines()
    assert rc == 0 and slept == 10.0
    assert lines[0].startswith("SATURATED machine 100% busy over 10.0 s on 16 logical CPUs; processes explain 100%")
    assert all(l.startswith("  ") for l in lines[1:]) and "claude.exe" in text


def test_main_leaves_its_own_python_out_of_the_shares():
    me = row(os.getpid(), "python.exe", kernel=0, user=0)
    me2 = row(os.getpid(), "python.exe", kernel=0, user=5_000_000_000)
    _, text, _ = fake_main([], [snap(me), snap(me2)])
    assert "python.exe" not in text.split("\n", 1)[1].split("not explained")[0]


def test_an_unreadable_snapshot_is_unknown_exit_2():
    rc, text, _ = fake_main([], ["not json", "[]"])
    assert rc == 2 and text.startswith("UNKNOWN a reading could not be taken")


def test_no_cpu_count_is_unknown():
    rc, text, _ = fake_main([], [], ncpu=0)
    assert rc == 2 and text.startswith("UNKNOWN the logical CPU count")


def test_main_clients_of_reads_one_snapshot_and_one_netstat():
    rc, text, _ = fake_main(["--clients-of", "11434"], [snap(row(500, "ollama.exe"), row(700, "window.exe"))], netstat=NETSTAT)
    assert rc == 0 and text.startswith("CLIENTS-SEEN") and "window.exe(700)" in text


def test_main_ollama_rate_reads_only_the_log(tmp_path):
    p = tmp_path / "ollama.log"
    p.write_text("\n".join(gin(s) for s in range(0, 100)) + "\n")
    rc, text, _ = fake_main(["--ollama-rate", "--ollama-log", str(p)], [])
    assert rc == 0 and text.startswith("POLLING-DOMINATED")


def test_main_ollama_rate_with_a_missing_log_is_unknown(tmp_path):
    rc, text, _ = fake_main(["--ollama-rate", "--ollama-log", str(tmp_path / "nope.log")], [])
    assert rc == 2 and text.startswith("UNKNOWN a reading could not be taken")


# ---------------------------------------------------------------- what the tool must never do

def test_the_module_cannot_stop_anything_and_writes_no_real_name_or_address():
    src = open(_PATH, encoding="utf-8").read()
    import re
    for needle in ("taskkill", "Stop-Process", ".kill(", ".terminate(", "os.kill", "TerminateProcess"):
        assert needle not in src, needle
    assert not re.search(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", src)
    assert not re.search(r"[\w.+-]+@[\w-]+\.(com|ai|net|org)\b", src)
