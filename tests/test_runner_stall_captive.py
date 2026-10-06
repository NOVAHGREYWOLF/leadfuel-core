"""NODE CAPTIVE-WAIT: the runner stall check treats a captive portal as 'wait', never as a runner
fault, and never restarts anything.

The real check talks to docker and gh. Here it runs against stub `docker` and `gh` programs that
log every call they get, with a stub captive probe whose answer each test chooses.
"""
import os
import re
import shutil
import stat
import subprocess

import pytest

CI = os.path.join(os.path.dirname(__file__), os.pardir, "node", "ci")
CHECK = os.path.join(CI, "runner_stall_check.sh")
WATCH = os.path.join(CI, "runner_stall_watch.sh")

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or shutil.which("timeout") is None,
                                reason="needs bash and coreutils timeout")

# A docker that is healthy unless the test says otherwise (TLS_RC=60 -> curl exits 60 in the
# container). Every call is appended to $STUB_LOG so a test can see what was and was not run.
DOCKER = r"""#!/usr/bin/env bash
echo "docker $*" >> "$STUB_LOG"
case "$*" in
  *inspect*) echo running ;;
  *" curl "*) echo -n 200; exit "${TLS_RC:-0}" ;;
  *"find /home/runner/_diag"*) echo /home/runner/_diag/Runner_1.log ;;
  *"ls -t"*) echo /home/runner/_diag/Runner_1.log ;;
  *"wc -l"*|*"grep -c"*) echo "${LOG_HITS:-0}" ;;
  *) echo 0 ;;
esac
"""
GH = r"""#!/usr/bin/env bash
echo "gh $*" >> "$STUB_LOG"
echo 0
"""
# The captive probe stub. PROBE_ANSWERS is a space-separated list consumed one per call (the last
# one repeats), so a test can say "ONLINE at the start, CAPTIVE at the end".
PROBE = r"""#!/usr/bin/env bash
echo probe >> "$STUB_LOG"
n=$(grep -c '^probe$' "$STUB_LOG")
set -- $PROBE_ANSWERS
[ "$n" -gt "$#" ] && n=$#
ans=${!n}
case "$ans" in
  CRASH) echo "Traceback: boom" >&2; exit 1 ;;
  GARBAGE) echo "all fine, probably"; exit 0 ;;
  SILENT) exit 0 ;;
  *) echo "$ans stub-reason"; echo "  windows: stub"; echo "  http: stub"; echo "  checked_at=now" ;;
esac
"""


def _write(path, text):
    with open(path, "w", newline="\n") as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


@pytest.fixture
def box(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _write(str(bindir / "docker"), DOCKER)
    _write(str(bindir / "gh"), GH)
    _write(str(tmp_path / "probe"), PROBE)
    log = tmp_path / "calls.log"
    log.write_text("")

    def run(answers, **env):
        e = dict(os.environ)
        e.update(PATH=str(bindir) + os.pathsep + e["PATH"], STUB_LOG=str(log),
                 CAPTIVE_PROBE="bash " + (tmp_path / "probe").as_posix(), PROBE_ANSWERS=answers,
                 CALL_S="20", PROBE_S="20", CONTAINERS="c1")
        e.update(env)
        e.pop("GH_TOKEN", None)
        p = subprocess.run([BASH, CHECK], capture_output=True, text=True, env=e, timeout=120)
        calls = log.read_text().splitlines()
        return p.returncode, p.stdout, calls
    return run


def first_line(out):
    return out.splitlines()[0]


def test_the_default_probe_command_is_python_with_the_windows_form_of_the_path(box, tmp_path):
    """Found by the first live run on this PC: the scheduled task passes /f/novah/ci/..., and
    python.exe cannot open that. Every other test sets CAPTIVE_PROBE itself, so none saw it."""
    bindir = tmp_path / "bin"
    _write(str(bindir / "cygpath"), '#!/usr/bin/env bash\necho "WIN:$2"\n')
    _write(str(bindir / "python"), '#!/usr/bin/env bash\necho "python $*" >> "$STUB_LOG"\necho "ONLINE stub"\n')
    rc, out, calls = box("ONLINE", CAPTIVE_PROBE="")     # empty -> the script's own default
    assert rc == 0 and first_line(out) == "OK", out
    pycalls = [c for c in calls if c.startswith("python ")]
    assert len(pycalls) == 1 and re.fullmatch(r"python WIN:.*[\\/]captive_probe\.py", pycalls[0]), calls
    assert "captive probe: ONLINE stub" in out


def docker_calls(calls):
    return [c for c in calls if c.startswith(("docker", "gh"))]


# ---------------------------------------------------------------- captive at the start

def test_captive_at_the_start_waits_and_does_not_touch_docker_or_gh(box):
    rc, out, calls = box("CAPTIVE")
    assert rc == 3
    assert first_line(out).startswith("CAPTIVE stub-reason"), out
    assert "CAPTIVE CAPTIVE" not in out
    assert "wait and retry later" in out and "Nothing was restarted" in out
    assert docker_calls(calls) == [], calls          # they would only hang or mislead
    assert calls.count("probe") == 1


# ---------------------------------------------------------------- captive at the end

def test_trouble_found_while_a_portal_came_up_is_held_back_not_called_a_runner_fault(box):
    rc, out, calls = box("ONLINE CAPTIVE", TLS_RC="60")
    assert rc == 3, out
    assert first_line(out).startswith("CAPTIVE stub-reason")
    assert "NOT a runner verdict" in out
    assert "held back (would be STALLED): c1: TLS to https://api.github.com/ fails" in out
    assert "STALLED" not in first_line(out)
    assert calls.count("probe") == 2


def test_captive_at_the_end_also_holds_back_an_unknown(box):
    rc, out, calls = box("UNKNOWN CAPTIVE", LOG_HITS="x")    # unreadable listener logs -> would be UNKNOWN
    assert rc == 3 and "held back (would be UNKNOWN)" in out


# ---------------------------------------------------------------- not captive: the old verdicts stand

def test_a_real_stall_with_the_network_online_is_still_stalled(box):
    rc, out, calls = box("ONLINE", TLS_RC="60")
    assert rc == 1 and first_line(out).startswith("STALLED"), out
    assert calls.count("probe") == 2                # asked again before calling it a runner fault


def test_all_probes_clean_is_ok_and_asks_the_portal_probe_only_once(box):
    rc, out, calls = box("ONLINE")
    assert rc == 0 and first_line(out) == "OK", out
    assert calls.count("probe") == 1
    assert "captive probe: ONLINE" in out


def test_a_probe_that_cannot_tell_does_not_turn_a_stall_into_anything_else(box):
    rc, out, calls = box("UNKNOWN", TLS_RC="60")
    assert rc == 1 and first_line(out).startswith("STALLED"), out
    assert "captive probe: UNKNOWN" in out


def test_a_probe_that_cannot_tell_does_not_turn_ok_into_a_fault_either(box):
    rc, out, calls = box("UNKNOWN")
    assert rc == 0 and first_line(out) == "OK"
    assert "captive probe: UNKNOWN" in out           # but it is visible


@pytest.mark.parametrize("answer", ["CRASH", "GARBAGE", "SILENT"])
def test_a_crashing_or_nonsense_probe_is_unknown_never_captive(box, answer):
    rc, out, calls = box(answer, TLS_RC="60")
    assert rc == 1 and first_line(out).startswith("STALLED"), out
    assert "captive probe: UNKNOWN captive probe gave no verdict" in out


def test_a_missing_probe_command_is_unknown_never_captive(box):
    rc, out, calls = box("CAPTIVE", CAPTIVE_PROBE="/nonexistent/probe-that-is-not-there", TLS_RC="60")
    assert rc == 1 and first_line(out).startswith("STALLED"), out


# ---------------------------------------------------------------- it never restarts anything

def test_no_run_ever_issues_a_mutating_docker_command(box):
    for answers, env in [("CAPTIVE", {}), ("ONLINE CAPTIVE", {"TLS_RC": "60"}), ("ONLINE", {"TLS_RC": "60"}),
                         ("ONLINE", {})]:
        rc, out, calls = box(answers, **env)
        bad = [c for c in calls if re.match(r"docker (restart|stop|start|rm|kill|run|create|pause|update)\b", c)]
        assert bad == [], (answers, bad)
        assert all(re.match(r"docker (inspect|exec)\b", c) or c.startswith(("gh api", "probe")) for c in calls), calls


def test_the_script_text_has_no_restart_or_deregister_command():
    with open(CHECK, encoding="utf-8") as f:
        code = "\n".join(line.split("#", 1)[0] for line in f.read().splitlines())
    for banned in ("docker restart", "docker stop", "docker start", "docker rm", "docker kill",
                   "docker run", "recreate_runners", "config.sh", "remove --token", "GH_TOKEN"):
        assert banned not in code, banned
    assert "--insecure" not in code and " -k " not in code and "curl -k" not in code


# ---------------------------------------------------------------- the watch wrapper

def test_the_watch_wrapper_records_exit_3_and_the_first_word(tmp_path):
    ci = tmp_path / "ci"
    ci.mkdir()
    shutil.copy(WATCH, ci / "runner_stall_watch.sh")
    _write(str(ci / "runner_stall_check.sh"), "#!/usr/bin/env bash\necho 'CAPTIVE stub'\necho '  detail'\nexit 3\n")
    p = subprocess.run([BASH, str(ci / "runner_stall_watch.sh")], capture_output=True, text=True, timeout=60)
    assert p.returncode == 3
    latest = (ci / "state" / "runner-stall.latest").read_text().splitlines()
    assert re.fullmatch(r"checked_at=\S+ exit=3", latest[0]) and latest[1] == "CAPTIVE stub"
    assert " exit=3 CAPTIVE stub" in (ci / "state" / "runner-stall.log").read_text()
