"""NODE desks-3-6: the owner-run script and the Python tool judge a leaked scan by the same rule.

One table of command lines is run through node/cpu_who.py (always) and through
node/windows/Stop-LeakedScans.ps1 (when PowerShell is on the PATH: it is on the CI runner and on
GREYWOLF). The script is dot-sourced, so only its functions load: nothing is listed and nothing is
stopped. The script also has to stay a dry run unless -Apply is typed.
"""
import importlib.util
import json
import os
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location("cpu_who", os.path.join(_HERE, os.pardir, "node", "cpu_who.py"))
cw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cw)
PS1 = os.path.abspath(os.path.join(_HERE, os.pardir, "node", "windows", "Stop-LeakedScans.ps1"))

GNU = r"C:\Program Files\Git\usr\bin\find.exe"
WIN = r"C:\Windows\System32\find.exe"

# (command line, executable path, age in minutes, bucket, search roots)
CASES = [
    ("find / -iname x", GNU, 131, "leak", ["/"]),
    ("find / -iname x", GNU, 29, "clean", ["/"]),
    ('find /i "needle"', WIN, 900, "clean", None),             # the Windows text filter: roots not asked
    ("find /f -name x", GNU, 60, "leak", ["/f"]),
    ("find /i -name x", None, 60, "ambiguous", ["/i"]),
    ("find -L / -name x", GNU, 60, "leak", ["/"]),
    ("find /f/work -name x", GNU, 900, "clean", ["/f/work"]),
    ("find F:\\ -name x", GNU, 60, "leak", ["F:\\"]),
    ("find C: -name x", GNU, 60, "clean", ["C:"]),
    ("", GNU, 60, "unreadable", None),
    ("find /tmp / -name x", GNU, 60, "leak", ["/tmp", "/"]),
    ('"C:\\Program Files\\Git\\usr\\bin\\find.exe" / -name x', GNU, 60, "leak", ["/"]),
    ("find . -name /", GNU, 60, "clean", ["."]),
    ("find / -name find x", GNU, 60, "leak", ["/"]),            # the old greedy pattern read `x` as the root
    ("find -name x", GNU, 900, "clean", []),
]


def python_bucket(cmd, exe, age):
    now = 1_800_000_000
    p = cw.Proc(1, 0, "find.exe", exe, cmd or None, now - age * 60, 1.0)
    leaks, amb, unread = cw.find_leaks([p], now)
    return "leak" if leaks else "ambiguous" if amb else "unreadable" if unread else "clean"


@pytest.mark.parametrize("cmd,exe,age,bucket,roots", CASES)
def test_python_side_of_the_table(cmd, exe, age, bucket, roots):
    assert python_bucket(cmd, exe, age) == bucket
    if roots is not None:
        assert cw.search_roots(cmd) == roots


DRIVER = r"""
param([string]$Script, [string]$CasesJson)
. $Script
$cases = Get-Content -Raw -Encoding UTF8 $CasesJson | ConvertFrom-Json
foreach ($c in $cases) {
    $created = (Get-Date).AddMinutes(-1 * [int]$c.age)
    $obj = [pscustomobject]@{ ExecutablePath = $c.exe; CommandLine = $c.cmd; CreationDate = $created }
    $r = Get-Leaks @($obj) 30
    $bucket = if ($r.Leaks.Count) { 'leak' } elseif ($r.Ambiguous.Count) { 'ambiguous' } elseif ($r.Unreadable.Count) { 'unreadable' } else { 'clean' }
    $roots = (@(Get-SearchRoots ([string]$c.cmd)) -join ';')
    Write-Output ("{0}|{1}" -f $bucket, $roots)
}
"""


def _shells():
    """Every PowerShell on this machine. GREYWOLF has both: the owner runs `powershell` (5.1), CI has pwsh."""
    return [s for s in (shutil.which("pwsh"), shutil.which("powershell")) if s]


@pytest.mark.skipif(not _shells(), reason="no PowerShell on this machine; the Python side of the table still ran")
@pytest.mark.parametrize("shell", _shells() or ["none"])
def test_the_script_agrees_with_the_python_rule_on_every_case(tmp_path, shell):
    cases = [{"cmd": c, "exe": e, "age": a} for c, e, a, _, _ in CASES]
    (tmp_path / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    (tmp_path / "driver.ps1").write_text(DRIVER, encoding="utf-8-sig")
    out = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(tmp_path / "driver.ps1"),
                          "-Script", PS1, "-CasesJson", str(tmp_path / "cases.json")],
                         capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    assert out.returncode == 0, out.stderr[-500:]
    got = out.stdout.strip().splitlines()
    assert len(got) == len(CASES), out.stdout
    for line, (cmd, exe, age, bucket, roots) in zip(got, CASES):
        b, r = line.split("|", 1)
        assert b == bucket, (cmd, exe, age, line)
        if roots is not None and bucket != "unreadable":
            assert (r.split(";") if r else []) == roots, (cmd, line)


def test_the_script_is_a_dry_run_unless_apply_is_typed():
    src = open(PS1, encoding="utf-8").read()
    assert "[switch]$Apply" in src
    # the only Stop-Process call sits after the -not $Apply branch has `continue`d
    before_stop = src[:src.index("Stop-Process -Id")]
    assert "if (-not $Apply)" in before_stop and "continue" in before_stop[before_stop.index("if (-not $Apply)"):]
    assert src.count("Stop-Process") == 1          # exactly one call in the whole script


def test_the_script_only_ever_stops_a_find_it_has_re_read():
    src = open(PS1, encoding="utf-8").read()
    assert "$now.Name -ne 'find.exe'" in src and "$now.CreationDate -ne $l.CreationDate" in src


def test_the_cmd_wrapper_bypasses_the_policy_for_one_process_and_adds_no_apply_of_its_own():
    cmd = open(os.path.join(os.path.dirname(PS1), "Stop-LeakedScans.cmd"), encoding="utf-8").read()
    runs = [l for l in cmd.splitlines() if l.lower().startswith("powershell")]
    assert len(runs) == 1
    assert "-ExecutionPolicy Bypass" in runs[0] and "%*" in runs[0] and "-Apply" not in runs[0]
    assert "Set-ExecutionPolicy" not in cmd            # it must not change a setting
