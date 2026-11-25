"""NODE lab plans (machines-6, P08, P14, desks-1-9, W09, machines-8) and library tools (library-6, W12, library-7).

Every address here is a placeholder (10.0.0.x, 100.64.x) or a documentation/public example (8.8.8.8).
Every token-shaped string is synthetic and built at run time.
"""
# ruff: noqa: E701, E702
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

_NODE = os.path.join(os.path.dirname(__file__), os.pardir, "node")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_NODE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lp = _load("lab_plans")
lt = _load("library_tools")
CFG = lp.load_config(path=os.path.join(os.path.dirname(__file__), "no-such-host-file.json"), placeholders=True)


def _plans(cfg=CFG):
    return (lp.machines6("2026-11-23", cfg), lp.p08(cfg, date="2026-11-23"), lp.p14(cfg, "20261123"),
            lp.desks19(cfg), lp.w09(cfg))


def _step(plan, shape_prefix):
    """The rendered command of the first step that is exactly this shape."""
    rx = lp._COMPILED[shape_prefix][0]
    return [c for _, c, _g in plan.steps if rx.fullmatch(c)][0]


# ---------- the allowlist ----------
def test_every_plan_renders_and_every_step_is_an_allowlisted_shape():
    for plan in _plans():
        text = plan.render()
        assert "set -eu" in text and "PLACEHOLDER" in text
        for _note, cmd, gated in plan.steps:
            lp.assert_safe(cmd, gated=gated)


BYPASSES = [
    # DOORS 212's list, verbatim shapes
    'r""m -f X', "X=r; ${X}m", "find /srv -delete", "rsync --del a b", "qm  destroy 901", "qm\tdestroy 901",
    'dd of="/dev/sda"', "cat /dev/zero > /dev/sda", "truncate -s 0 /x", "unlink /x", "curl\thttp://x",
    "pip3 install x", "apt -y install x", "git clone https://x", "nc 10.0.0.1 80", "scp f root@8.8.8.8:/",
    "ssh root@8.8.8.8",
    # the original denylist cases
    "rm -rf /x", "wipefs -a /dev/sda", "rsync --delete a b", "dd if=a of=/dev/sda", "mv a b", "qm destroy 901",
    "apt install x", "curl http://x",
    # near-misses of real shapes
    "qm stop 9101; rm -rf /", "qm stop 9101\nrm -rf /", "qm stop $(echo 901)", "qm stop 9101 ", " qm stop 9101",
    "pvesm list backup-store --vmid 901; reboot", "find /srv -xdev -type f -mtime +365 -print0 > /x -delete",
    "find /srv/../ -xdev -type f -mtime +1 -print0 > /x", "smartctl -a /dev/sda; dd if=/dev/zero of=/dev/sda",
]


@pytest.mark.parametrize("cmd", BYPASSES)
def test_guard_refuses_bypass_strings(cmd):
    with pytest.raises(lp.Refused):
        lp.assert_safe(cmd)
    with pytest.raises(lp.Refused):
        lp.assert_safe(cmd, gated=True)


def test_slot_values_are_validated_so_shapes_cannot_carry_payloads():
    for bad in ("/x; rm -rf /", "/x y", "/x'", "/a/../b", "/dev/sda", "/x$(id)", "/x\t"):
        with pytest.raises(lp.Refused):
            lp.render_shape("cold-list", root=bad, days=1, lst="/root/l")
    with pytest.raises(lp.Refused):
        lp.render_shape("vm-stop", scratch="901")      # only a 91xx scratch id


def test_gated_only_shapes_are_refused_ungated():
    for key in ("destroy-scratch", "vzdump-job", "rsync-copy", "ddrescue-1", "ddrescue-2"):
        assert lp.SHAPES[key][1] is True
    with pytest.raises(lp.Refused):
        lp.assert_safe("qm destroy 9101 --purge")
    assert lp.assert_safe("qm destroy 9101 --purge", gated=True)
    with pytest.raises(lp.Refused):
        lp.assert_safe("qm destroy 901 --purge", gated=True)


def test_public_ip_anywhere_in_a_command_is_refused():
    good = _step(lp.machines6("DATE", CFG), "no-overwrite")
    lp.assert_safe(good)
    with pytest.raises(lp.Refused):
        lp.assert_safe(good.replace("10.0.0.11", "8.8.8.8"))
    with pytest.raises(lp.Refused):
        lp.assert_safe("echo 8.8.8.8")


def test_unlisted_alias_is_refused_and_listed_alias_passes():
    with pytest.raises(lp.Refused):
        lp.render_shape("no-overwrite", dst="backup-box", tarf="/x.tar")
    assert "backup-box" in lp.render_shape("no-overwrite", aliases=("backup-box",), dst="backup-box", tarf="/x.tar")


# ---------- --date ----------
@pytest.mark.parametrize("date", ['D; r""m -f X', "$(wget\thttp://x)", "2026-11-23;id", "2026/11/23", "", "../x"])
def test_date_is_digits_only(date, capsys):
    assert lp.main(["machines-6", "--placeholders", "--date", date], out=io.StringIO()) == 2
    assert "REFUSED" in capsys.readouterr().err
    with pytest.raises(lp.Refused):
        lp.machines6(date, CFG)


@pytest.mark.parametrize("date", ["2026-11-23", "20261123", "DATE"])
def test_date_accepts_digits(date):
    assert date in lp.machines6(date, CFG).render()


# ---------- host config ----------
def test_cli_refuses_without_a_host_file_and_renders_placeholders_when_asked(tmp_path, capsys):
    missing = str(tmp_path / "none.json")
    assert lp.main(["W09", "--hosts", missing], out=io.StringIO()) == 2
    assert "no host file" in capsys.readouterr().err
    buf = io.StringIO()
    assert lp.main(["W09", "--hosts", missing, "--placeholders"], out=buf) == 0
    assert "pct set 905" in buf.getvalue() and "PLACEHOLDER" in buf.getvalue()


def test_local_host_file_overrides_placeholders_and_is_lan_checked(tmp_path):
    f = tmp_path / "hosts.json"
    f.write_text(json.dumps({"hosts": {"backup": "root@100.64.1.2"}, "aliases": ["pve-a"],
                             "ids": {"gpu_ct": 333}}))
    cfg = lp.load_config(str(f))
    assert cfg["placeholder"] is False and cfg["hosts"]["backup"] == "root@100.64.1.2"
    assert "100.64.1.2" in lp.machines6("DATE", cfg).render() and "pct set 333" in lp.w09(cfg).render()
    f.write_text(json.dumps({"hosts": {"backup": "root@8.8.8.8"}}))
    with pytest.raises(lp.Refused):
        lp.load_config(str(f))
    f.write_text(json.dumps({"hosts": {"bakup": "root@10.0.0.1"}}))
    with pytest.raises(lp.Refused):
        lp.load_config(str(f))


def test_the_local_host_file_is_git_ignored():
    gi = open(os.path.join(os.path.dirname(__file__), os.pardir, ".gitignore"), encoding="utf-8").read()
    assert "node/lab_hosts.local.json" in gi.split()


def test_no_real_infrastructure_identifiers_in_the_tracked_files():
    """Guard for this PR's leak class: only placeholder or documentation addresses in these files."""
    import re
    root = os.path.join(os.path.dirname(__file__), os.pardir)
    for rel in ("node/lab_plans.py", "node/library_tools.py", "docs/NODE_LAB_PLANS.md", "tests/test_node_lab_and_library.py"):
        text = open(os.path.join(root, rel), encoding="utf-8").read()
        for ip in re.findall(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])", text):
            assert ip.startswith(("10.0.0.", "100.64.", "127.0.0.", "8.8.8.8", "169.254.1.1", "0.0.0.0",
                                  "172.16.0.0", "192.168.0.0")), \
                (rel, "non-placeholder address")
        assert not re.search(r"C:\\Users\\(?!<user>)\w", text), (rel, "a real user path")


# ---------- plan content ----------
def test_only_the_scratch_vm_can_be_destroyed_and_it_is_gated():
    p = lp.desks19(CFG, scratch="9101")
    d = [s for s in p.steps if "destroy" in s[1]]
    assert len(d) == 1 and d[0][2] and d[0][1] == "qm destroy 9101 --purge"
    assert "# GATED: qm destroy 9101" in p.render()
    with pytest.raises(lp.Refused):
        lp.desks19(CFG, scratch="901")


def test_restore_boots_with_links_down_not_on_the_source_vms_network():
    text = lp.desks19(CFG).render()
    assert "link_down=1" in text and text.index("link_down") < text.index("qm start")


def test_salvage_disk_is_never_a_write_target_and_copies_are_gated():
    p = lp.p14(CFG, "DATE")
    for _, cmd, gated in p.steps:
        assert "of=/dev/" not in cmd
        if "ddrescue" in cmd:
            assert gated and cmd.split()[-3] == "/dev/sdz"   # the disk is the input; image and map follow
    assert "--setro" in p.render()


def test_p08_never_emits_a_removal_and_lists_candidates():
    text = lp.p08(CFG, date="DATE").render()
    assert "rm " not in text and "--remove-source" not in text and "sha256sum" in text
    assert "comm -12" in text and ".candidates" in text and "sort -k2" not in text   # whole-line sort for comm


def test_lan_only():
    with pytest.raises(lp.Refused):
        lp.check_lan("root@8.8.8.8")
    for bad in ("::1", "169.254.1.1", "0.0.0.0", "unlisted-name"):
        with pytest.raises(lp.Refused):
            lp.check_lan(bad)
    assert lp.check_lan("root@100.64.0.9") and lp.check_lan("root@10.0.0.11") and lp.check_lan("x", ("x",))


def test_machines6_verifies_both_ends_and_drafts_vzdump_gated():
    p = lp.machines6("DATE", CFG)
    text = p.render()
    assert text.count("sha256sum") >= 2 and "MISMATCH-or-UNKNOWN" in text and "set -C" in text
    assert [s for s in p.steps if "pvesh create" in s[1]][0][2] is True


def test_syncthing_is_sendonly_and_flags_placeholders():
    cfg = lp.surface_syncthing(CFG)
    assert all(f["type"] == "sendonly" for f in cfg["sender"]) and cfg["device_id_is_placeholder"]
    assert cfg["hosts_are_placeholders"] and "ignoreDelete" in cfg["receiver_note"]
    assert all(f["path"].startswith("C:\\Users\\<user>") for f in cfg["sender"])


def test_cli_prints_and_refuses(capsys):
    buf = io.StringIO()
    assert lp.main(["W09", "--placeholders"], out=buf) == 0 and "pct set 905" in buf.getvalue()
    assert lp.main(["P08", "--placeholders", "--date", "x;id"], out=io.StringIO()) == 2


# ---------- the guards really stop under sh (set -eu does not cover !, pipelines or && lists) ----------
def _sh():
    for c in (shutil.which("sh"), r"C:\Program Files\Git\bin\sh.exe", r"C:\Program Files\Git\usr\bin\sh.exe"):
        if c and os.path.exists(c):
            return c
    return None


SH = _sh()
STUB = '#!/bin/sh\nn=$(basename "$0")\neval "o=\\${STUB_OUT_$n:-}"\neval "r=\\${STUB_RC_$n:-0}"\n' \
       '[ -z "$o" ] || printf "%b\\n" "$o"\nexit "$r"\n'
STUBBED = ("ssh", "pgrep", "df", "pvesh", "pvesm", "qm", "blockdev", "mountpoint", "mkdir", "sleep", "pct", "awk")


def _run(tmp_path, cmd, stub_awk=False, **stubs):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name in STUBBED:
        if name == "awk" and not stub_awk:
            continue
        p = bindir / name
        p.write_text(STUB, newline="\n")
        p.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    for k, v in stubs.items():
        kind, name = k.split("_", 1)
        env[f"STUB_{kind.upper()}_{name}"] = str(v)
    script = "set -eu\n" + cmd + "\necho REACHED\n"
    r = subprocess.run([SH, "-c", script], env=env, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout


M6, P8, P14_, D19, W9 = _plans()
GUARDS = [
    # (plan, shape, stubs that must STOP the script, stubs that must PASS it)
    ("busy running", M6, "busy-check", {"rc_pgrep": 0}, {"rc_pgrep": 1}),
    ("busy pgrep error", M6, "busy-check", {"rc_pgrep": 2}, {"rc_pgrep": 1}),
    ("space ssh fails", M6, "space-remote", {"rc_ssh": 255}, {"out_ssh": "  100"}),
    ("space too small", M6, "space-remote", {"out_ssh": "  5"}, {"out_ssh": "  100"}),
    ("archive exists", M6, "no-overwrite", {"rc_ssh": 0}, {"rc_ssh": 1}),
    ("archive unknown", M6, "no-overwrite", {"rc_ssh": 255}, {"rc_ssh": 1}),
    ("sha empty", M6, "sha-both", {"rc_ssh": 255}, {"out_ssh": "a" * 64 + "  -"}),
    ("archive unreadable", M6, "tar-list", {"rc_ssh": 2}, {"out_ssh": "x"}),
    ("df fails", P8, "usage", {"rc_df": 1}, {"out_df": "/dev/x 10 5 5 50% /srv/library"}),
    ("not mounted", P14_, "mounted", {"rc_mountpoint": 1}, {"rc_mountpoint": 0}),
    ("local df fails", P14_, "space-local", {"rc_df": 1}, {"out_df": "Avail\\n  900"}),
    ("not read-only", P14_, "setro", {"out_blockdev": "0"}, {"out_blockdev": "1"}),
    ("storage offline", D19, "storage-online", {"out_pvesm": "Name Type Status\\nbackup-store dir inactive"},
     {"out_pvesm": "Name Type Status\\nbackup-store dir active"}),
    ("storage unreadable", D19, "storage-online", {"rc_pvesm": 1},
     {"out_pvesm": "Name Type Status\\nbackup-store dir active"}),
    ("scratch taken", D19, "id-free", {"rc_pvesh": 2}, {"rc_pvesh": 0}),
    ("nic still up", D19, "links-down", {"out_qm": "net0: virtio=AA,bridge=vmbr0"},
     {"out_qm": "net0: virtio=AA,bridge=vmbr0,link_down=1"}),
    ("qm config fails", D19, "links-down", {"rc_qm": 1}, {"out_qm": "net0: virtio=AA,link_down=1"}),
    ("not running", D19, "boot-check", {"out_qm": "status: stopped"}, {"out_qm": "status: running"}),
]


@pytest.mark.skipif(SH is None, reason="no POSIX sh on this machine (CI has one)")
@pytest.mark.parametrize("label,plan,shape,stop,ok", GUARDS, ids=[g[0] for g in GUARDS])
def test_guard_line_really_stops_under_set_eu(tmp_path, label, plan, shape, stop, ok):
    cmd = _step(plan, shape)
    rc, out = _run(tmp_path, cmd, **stop)
    assert rc != 0 and "REACHED" not in out, (label, out)
    rc, out = _run(tmp_path, cmd, **ok)          # the control: the same line passes when the state is good
    assert rc == 0 and "REACHED" in out, (label, out)


@pytest.mark.skipif(SH is None, reason="no POSIX sh on this machine (CI has one)")
def test_headroom_stops_when_meminfo_is_unreadable_or_short(tmp_path):
    cmd = _step(W9, "headroom")
    for awk_out in ("", "100", "x"):
        rc, out = _run(tmp_path, cmd, stub_awk=True, out_awk=awk_out)
        assert rc != 0 and "REACHED" not in out, awk_out
    rc, out = _run(tmp_path, cmd, stub_awk=True, out_awk="40000")
    assert rc == 0 and "REACHED" in out


@pytest.mark.skipif(SH is None, reason="no POSIX sh on this machine (CI has one)")
def test_hash_image_and_task_logs_stop_when_nothing_is_there(tmp_path):
    for cmd in (_step(P14_, "hash-image"), _step(D19, "task-logs")):
        rc, out = _run(tmp_path, cmd)
        assert rc != 0 and "REACHED" not in out


# ---------- library ----------
def _tok(prefix, n=36):
    return prefix + ("A1b2C3d4" * 8)[:n]       # synthetic: built at run time, never a real credential


def test_scan_clean_hits_and_unknown(tmp_path):
    clean = tmp_path / "a.md"; clean.write_text("nothing here\npassword: <your-password>\n")
    dirty = tmp_path / "b.md"; dirty.write_text("ok\napi_key = abcdefghijklmnop1234\n-----BEGIN RSA PRIVATE KEY-----\n")
    r1, r2, r3 = lt.scan_file(str(clean)), lt.scan_file(str(dirty)), lt.scan_file(str(tmp_path / "missing"))
    assert r1["verdict"] == "CLEAN" and r1["sha256"]
    assert r2["verdict"] == "HITS" and r2["hits"]["assigned-secret"] == [2] and r2["hits"]["private-key-block"] == [3]
    assert "abcdefghijklmnop" not in json.dumps(r2)
    assert r3["verdict"] == "UNKNOWN"


@pytest.mark.parametrize("line", [
    "token = {t}  # see example",
    "{t} ... and more",
    "your-config: {t}",
    "placeholder text then {t}",
    "x = 'example' ; real = {t}",
])
def test_placeholder_words_elsewhere_on_the_line_do_not_hide_a_token(tmp_path, line):
    f = tmp_path / "t.md"
    t = _tok("ghp_")
    f.write_text("intro\n" + line.format(t=t) + "\n")
    r = lt.scan_file(str(f))
    assert r["verdict"] == "HITS" and r["hits"]["github-token"] == [2]
    assert t not in json.dumps(r)


def test_placeholder_inside_the_matched_span_is_still_a_placeholder(tmp_path):
    f = tmp_path / "p.md"
    f.write_text("token: ghp_" + "x" * 36 + "\nkey: sk-EXAMPLE" + "0" * 24 + "\n")
    assert lt.scan_file(str(f))["verdict"] == "CLEAN"


@pytest.mark.parametrize("enc", ["utf-16", "utf-16-le", "utf-16-be"])
def test_utf16_files_are_unknown_not_clean(tmp_path, enc):
    f = tmp_path / "w.txt"
    f.write_bytes(("token = " + _tok("ghp_") + "\n").encode(enc))
    r = lt.scan_file(str(f))
    assert r["verdict"] == "UNKNOWN" and r["sha256"]


def test_binary_and_non_utf8_files_are_unknown(tmp_path):
    b = tmp_path / "b.bin"; b.write_bytes(b"abc\x00def")
    n = tmp_path / "n.txt"; n.write_bytes(b"caf\xe9 token\n")
    assert lt.scan_file(str(b))["verdict"] == "UNKNOWN"
    assert lt.scan_file(str(n))["verdict"] == "UNKNOWN"
    s = tmp_path / "s.txt"; s.write_bytes(b"\xef\xbb\xbfplain utf-8 with a BOM\n")
    assert lt.scan_file(str(s))["verdict"] == "CLEAN"


def _manifest(tmp_path, rows):
    p = tmp_path / "M.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return str(p)


def test_dups_pick_filed_repo_copy_over_unfiled_mirror(tmp_path):
    rows = [{"path": "artifacts/x/index.html", "sha256": "a" * 64, "project": "unfiled", "kind": "platform-artifacts", "bytes": 5},
            {"path": "local-documents/hub/x.html", "sha256": "a" * 64, "project": "hub", "kind": "repo-documents", "bytes": 5},
            {"path": "solo.md", "sha256": "b" * 64, "project": "hub", "kind": "repo-documents", "bytes": 1}]
    g = lt.dup_groups(_manifest(tmp_path, rows))
    assert len(g) == 1 and g[0]["canonical"] == "local-documents/hub/x.html" and g[0]["copies"] == 2


def test_compare_counts_and_unknown_when_empty(tmp_path):
    m = _manifest(tmp_path, [{"path": "p", "sha256": "a" * 64}])
    h = tmp_path / "h.txt"
    h.write_text(f"{'a' * 64}  /srv/library/_raw/one\n{'c' * 64}  /srv/library/_raw/two\nnot a line\n")
    r = lt.compare(m, str(h))
    assert (r["in_library"], r["not_in_library"], r["unparseable_lines"]) == (1, 1, 1)
    e = tmp_path / "e.txt"; e.write_text("")
    assert lt.compare(m, str(e))["unknown_if_zero_lines"] is True
