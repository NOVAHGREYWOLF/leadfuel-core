"""NODE cluster files part 1: the inventory of every drive and device. A machine that cannot be read is
`unknown` and never empty; a section that failed keeps its last-known rows as `stale`; a tool that is
not installed is `absent`; a size nobody reported is null, never 0; the collector only ever sends a
fixed read script and refuses a public address. Fixtures are synthetic (no real serial or layout)."""
import importlib.util
import json
import os
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


ci = _load("cluster_inventory")

LSBLK = {"blockdevices": [
    {"name": "sda", "kname": "sda", "type": "disk", "size": 250000000000, "fstype": None, "mountpoint": None,
     "model": "Acme SSD 250GB", "serial": "SN-FAKE-1", "label": None, "ro": True, "rota": False, "pkname": None,
     "fsused": None, "tran": "sata", "rm": False,
     "children": [{"name": "sda1", "kname": "sda1", "type": "part", "size": 249000000000, "fstype": "ntfs",
                   "mountpoint": None, "model": None, "serial": None, "label": "Old", "ro": True, "rota": False,
                   "pkname": "sda", "fsused": None, "tran": None, "rm": False}]},
    {"name": "nvme0n1", "kname": "nvme0n1", "type": "disk", "size": 500000000000, "fstype": None,
     "mountpoint": None, "model": "Acme NVMe", "serial": "SN-FAKE-2", "label": None, "ro": False, "rota": False,
     "pkname": None, "fsused": None, "tran": "nvme", "rm": False,
     "children": [{"name": "nvme0n1p3", "kname": "nvme0n1p3", "type": "part", "size": 400000000000,
                   "fstype": "LVM2_member", "mountpoint": None, "model": None, "serial": None, "label": None,
                   "ro": False, "rota": False, "pkname": "nvme0n1", "fsused": None, "tran": None, "rm": False,
                   "children": [
                       {"name": "pve-root", "kname": "dm-1", "type": "lvm", "size": 100000000000, "fstype": "ext4",
                        "mountpoint": "/", "model": None, "serial": None, "label": None, "ro": False,
                        "rota": False, "pkname": "nvme0n1p3", "fsused": None, "tran": None, "rm": False},
                       {"name": "pve-swap", "kname": "dm-0", "type": "lvm", "size": 8000000000, "fstype": "swap",
                        "mountpoint": "[SWAP]", "model": None, "serial": None, "label": None, "ro": False,
                        "rota": False, "pkname": "nvme0n1p3", "fsused": None, "tran": None, "rm": False}]}]},
    {"name": "loop0", "kname": "loop0", "type": "loop", "size": 1000, "fstype": None, "mountpoint": None},
]}
DF = """Filesystem                  Type  1024-blocks      Used Available Capacity Mounted on
/dev/mapper/pve-root        ext4     97656250  48828125  43000000      54% /
tmpfs                       tmpfs     1000000         0   1000000       0% /run
10.20.0.51:/mnt/backup/d    nfs4   7000000000 3500000000 3400000000      51% /mnt/pve/r710-backup
"""
PVESM = """Name               Type     Status     Total (KiB)      Used (KiB) Available (KiB)        %
local               dir     active        98497780        51766660        41681572   52.56%
local-lvm       lvmthin     active       353492992       305205849        48287142   86.34%
nas                 nfs   inactive               0               0               0    0.00%
"""
LVS = ("  data|pve|361000000000|80.00||twi-aotz--\n"
       "  root|pve|100000000000||| -wi-ao----\n"
       "  vm-100-disk-1|pve|50000000000|40.00|data|Vwi-a-tz--\n"
       "  vm-104-disk-0|pve|40000000000|||Vwi---tz--\n")
VGS = "  pve|400000000000|16000000000\n"
QM = """      VMID NAME                 STATUS     MEM(MB)    BOOTDISK(GB) PID
       100 novah-personal       stopped    16384            50.00 0
       101 opnsense-fw          running    4096             20.00 4242
"""
PCT = """VMID       Status     Lock         Name
105        stopped                 ai-gpu
"""
QMCONF = """#FILE /etc/pve/qemu-server/100.conf
name: novah-personal
scsi0: local-lvm:vm-100-disk-1,iothread=1,size=50G
ide2: none,media=cdrom
efidisk0: local-lvm:vm-100-disk-0,efitype=4m,size=4M
#FILE /etc/pve/qemu-server/101.conf
name: opnsense-fw
virtio0: local:101/vm-101-disk-0.qcow2,size=20G
sata1: /dev/disk/by-id/fake-passthrough,size=1T
"""
PCTCONF = """#FILE /etc/pve/lxc/105.conf
hostname: ai-gpu
rootfs: local-lvm:vm-105-disk-0,size=12G
mp0: /var/lib/models,mp=/models
"""


def sec(name, rc, text=""):
    return f"@@BEGIN {name}\n{text}\n@@END {name} rc={rc}\n"


def linux_raw(**over):
    s = {"now": (0, "1790000000"), "lsblk": (0, json.dumps(LSBLK)), "df": (0, DF), "zpool": (0, ""),
         "zfs": (0, ""), "vgs": (0, VGS), "lvs": (0, LVS), "pvesm": (0, PVESM), "qm": (0, QM), "pct": (0, PCT),
         "qmconf": (0, QMCONF), "pctconf": (0, PCTCONF)}
    s.update(over)
    return "".join(sec(n, rc, t) for n, (rc, t) in s.items())


LINUX = {"id": "overlord", "role": "host", "os": "linux", "route": {"kind": "ssh", "host": "10.20.0.50"}}
WIN = {"id": "greywolf", "role": "pc", "os": "windows", "route": {"kind": "local"}}


def by(rows, kind=None, device=None):
    return [r for r in rows if (kind is None or r["kind"] == kind) and (device is None or r["device"] == device)]


# ------------------------------------------------------------------------------ linux parsing
def test_lsblk_tree_sizes_and_df_join():
    df = ci.df_by_mount(ci.parse_df(DF))
    rows = ci.parse_lsblk(json.dumps(LSBLK), "overlord", df)
    assert {r["device"] for r in rows} == {"/dev/sda", "/dev/sda1", "/dev/nvme0n1", "/dev/nvme0n1p3",
                                            "/dev/pve-root", "/dev/pve-swap"}      # loop skipped
    root = by(rows, device="/dev/pve-root")[0]
    assert (root["mount"], root["size"], root["used"], root["free"]) == ("/", 100000000000, 48828125 * 1024, 43000000 * 1024)
    assert by(rows, device="/dev/pve-swap")[0]["fs"] == "swap"
    sda1 = by(rows, device="/dev/sda1")[0]
    assert sda1["used"] is None and sda1["free"] is None, "an unmounted fs has no used, not 0"
    assert sda1["parent"] == "/dev/sda" and sda1["state"] == "read-only" and sda1["label"] == "Old"
    assert by(rows, device="/dev/sda")[0]["model"] == "Acme SSD 250GB"


def test_lsblk_repeated_device_listed_once():
    twice = {"blockdevices": [
        {"name": "a", "type": "disk", "size": 1, "children": [{"name": "pool", "type": "lvm", "size": 1}]},
        {"name": "b", "type": "disk", "size": 1, "children": [{"name": "pool", "type": "lvm", "size": 1}]}]}
    rows = ci.parse_lsblk(json.dumps(twice), "m", {})
    assert len(by(rows, device="/dev/pool")) == 1


def test_df_and_network_mounts():
    rows = ci.parse_network_mounts(ci.parse_df(DF), "overlord")
    assert len(rows) == 1 and rows[0]["fs"] == "nfs4" and rows[0]["mount"] == "/mnt/pve/r710-backup"
    assert rows[0]["size"] == 7000000000 * 1024


def test_zero_is_kept_and_missing_is_none():
    df = ci.parse_df("Filesystem Type 1K-blocks Used Available Use% Mounted on\n/dev/x ext4 100 0 100 0% /m\n")
    assert df[0]["used"] == 0, "a genuinely empty fs reports 0"
    assert ci.to_int("-") is None and ci.to_int("") is None and ci.to_int(None) is None and ci.to_int(0) == 0


def test_lvs_thin_used_from_data_percent():
    rows = ci.parse_lvs(LVS, "overlord")
    d = {r["device"]: r for r in rows}
    assert d["pve/data"]["used"] == int(361000000000 * 0.8) and d["pve/data"]["note"] == "thin pool"
    assert d["pve/vm-100-disk-1"]["used"] == 20000000000 and d["pve/vm-100-disk-1"]["fs"] == "lvm-thin"
    assert d["pve/root"]["used"] is None and d["pve/root"]["fs"] == "lvm"
    assert d["pve/vm-104-disk-0"]["used"] is None


def test_vgs_pvesm_zpool_zfs():
    vg = ci.parse_vgs(VGS, "m")[0]
    assert (vg["size"], vg["free"], vg["used"]) == (400000000000, 16000000000, 384000000000)
    pools = {r["device"]: r for r in ci.parse_pvesm(PVESM, "m")}
    assert pools["local-lvm"]["size"] == 353492992 * 1024 and pools["nas"]["state"] == "inactive"
    zp = ci.parse_zpool("tank\t1000\t400\t600\t-\t-\t1%\t40\t1.00x\tONLINE\t-\n", "m")[0]
    assert (zp["device"], zp["size"], zp["used"], zp["free"], zp["state"]) == ("tank", 1000, 400, 600, "ONLINE")
    zf = ci.parse_zfs("tank/data\t300\t700\t/tank/data\ntank/v\t5\t700\t-\n", "m")
    assert zf[0]["mount"] == "/tank/data" and zf[0]["size"] == 1000 and zf[1]["mount"] is None


def test_guest_disks_vm_ct_and_thin_used():
    lv_used = {r["device"].split("/", 1)[1]: r["used"] for r in ci.parse_lvs(LVS, "m") if r["used"] is not None}
    rows = ci.parse_guest_disks("m", ci.parse_guest_list(QM), ci.parse_guest_list(PCT),
                                ci.parse_confdisks(QMCONF), ci.parse_confdisks(PCTCONF), lv_used)
    d = {r["device"]: r for r in rows}
    assert "vm100:ide2" not in d, "a cdrom is not a disk"
    assert d["vm100:scsi0"]["size"] == 50 * (1 << 30) and d["vm100:scsi0"]["used"] == 20000000000
    assert d["vm100:scsi0"]["state"] == "stopped" and "novah-personal" in d["vm100:scsi0"]["note"]
    assert d["vm100:efidisk0"]["size"] == 4 * (1 << 20)
    assert d["vm101:virtio0"]["used"] is None and "passthrough" in d["vm101:sata1"]["note"]
    assert d["vm101:sata1"]["size"] == 1 << 40
    assert d["ct105:rootfs"]["kind"] == "ct-mount" and d["ct105:rootfs"]["size"] == 12 * (1 << 30)
    assert d["ct105:mp0"]["mount"] == "/models" and d["ct105:mp0"]["size"] is None


def test_guest_config_never_reads_secrets():
    """The remote awk only lets disk and name lines through; a cipassword line is not one of them."""
    script = ci.LINUX_SCRIPT
    assert "cipassword" not in script and "sshkeys" not in script and "ipconfig" not in script
    awk = [l for l in script.splitlines() if "awk" in l][0]
    for key in ("name", "hostname", "scsi", "virtio", "sata", "ide", "efidisk", "tpmstate", "rootfs", "mp"):
        assert key in awk
    assert "password" not in awk and "ssh" not in awk and "net" not in awk


def test_read_script_is_read_only():
    forbidden = ("rm ", "mv ", "dd ", "mkfs", "mount ", "umount", "apt", "pvesm alloc", "qm start", "qm stop",
                 "zpool create", "zfs destroy", "tee ", ">>", "chmod", "systemctl", "wipefs", "sgdisk")
    for tok in forbidden:
        assert tok not in ci.LINUX_SCRIPT, tok
    for tok in ("Set-", "Remove-", "New-", "Format-", "Clear-", "Out-File", "Start-", "Stop-"):
        assert tok not in ci.WINDOWS_SCRIPT.replace("Format-", ""), tok
    assert "Get-CimInstance" in ci.WINDOWS_SCRIPT and "Get-Partition" in ci.WINDOWS_SCRIPT


# ------------------------------------------------------------------- sections, absent, unknown
def test_split_sections_rc_and_truncated():
    s = ci.split_sections("@@BEGIN a\nx\n@@END a rc=0\n@@BEGIN b\npartial")
    assert s["a"] == {"rc": 0, "text": "x"} and s["b"]["rc"] is None


def test_verified_machine_counts_and_absent_not_failure():
    rows, summ = ci.build_machine(LINUX, linux_raw(zpool=(127, ""), zfs=(127, "")), None, [], {}, "T")
    assert summ["status"] == "verified" and summ["sections"]["zpool"] == "absent"
    assert summ["reason"] is None and summ["last_seen"] == "2026-09-21T14:13:20Z"
    assert all(r["status"] == "verified" for r in rows) and summ["rows"] == len(rows) > 15


def test_failed_section_is_partial_and_carries_stale_rows():
    prev = [ci.row("overlord", "lvm-lv", "pve/old", size=5, source="lvs", status="verified" , last_seen="OLD"),
            ci.row("overlord", "disk", "/dev/zzz", size=5, source="lsblk", last_seen="OLD")]
    rows, summ = ci.build_machine(LINUX, linux_raw(lvs=(1, "")), None, prev, {}, "T")
    assert summ["status"] == "partial" and "lvs" in summ["reason"]
    stale = [r for r in rows if r["status"] == "stale"]
    assert [r["device"] for r in stale] == ["pve/old"], "only the failed section's rows are carried"
    assert stale[0]["last_seen"] == "OLD"
    assert not by(rows, kind="lvm-lv", device="pve/vm-100-disk-1"), "no fresh lvm rows were invented"


def test_truncated_section_is_unknown_not_empty():
    raw = linux_raw().replace("@@END lvs rc=0", "")
    _, summ = ci.build_machine(LINUX, raw, None, [], {}, "T")
    assert summ["sections"]["lvs"] == "unknown" and summ["status"] == "partial"


def test_unreachable_keeps_last_known_as_stale():
    prev = [ci.row("overlord", "disk", "/dev/sda", size=9, source="lsblk", last_seen="2026-11-20T00:00:00Z")]
    rows, summ = ci.build_machine(LINUX, None, "timed out", prev, {"overlord": "2026-11-20T00:00:00Z"}, "T")
    assert summ["status"] == "unknown" and summ["reason"] == "timed out"
    assert summ["last_seen"] == "2026-11-20T00:00:00Z"
    assert [(r["device"], r["status"], r["last_seen"]) for r in rows] == [("/dev/sda", "stale", "2026-11-20T00:00:00Z")]


def test_unreachable_never_zero_rows():
    rows, summ = ci.build_machine(LINUX, None, "no route", [], {}, "T")
    assert len(rows) == 1 and rows[0]["status"] == "unknown" and rows[0]["kind"] == "machine"
    assert rows[0]["size"] is None and summ["status"] == "unknown" and summ["last_seen"] is None


def test_garbage_answer_is_unknown():
    rows, summ = ci.build_machine(WIN, "@@JSON {not json @@ENDJSON", None, [], {}, "T")
    assert summ["status"] == "unknown" and rows[0]["status"] == "unknown"
    rows, summ = ci.build_machine(LINUX, linux_raw(lsblk=(0, "{broken")), None, [], {}, "T")
    assert summ["status"] == "unknown" and "parsed" in summ["reason"]


def test_reachable_but_zero_rows_is_not_verified():
    empty = linux_raw(lsblk=(1, ""), df=(1, ""), vgs=(127, ""), lvs=(127, ""), pvesm=(127, ""), qm=(127, ""),
                      pct=(127, ""), qmconf=(127, ""), pctconf=(127, ""), zpool=(127, ""), zfs=(127, ""))
    rows, summ = ci.build_machine(LINUX, empty, None, [], {}, "T")
    assert summ["status"] == "unknown" and rows[0]["status"] == "unknown"


# -------------------------------------------------------------------------------- windows
WINPAYLOAD = {"now": 1790000000, "errors": {},
              "disks": [{"index": 0, "model": "Fake NVMe", "serial": "SN-W", "size": 500000000000, "iface": "SCSI", "media": "Fixed"}],
              "logical": [{"id": "C:", "label": "OS", "fs": "NTFS", "size": 400000000000, "free": 100000000000, "type": 3, "provider": None},
                          {"id": "G:", "label": "Drive", "fs": "NTFS", "size": None, "free": None, "type": 4, "provider": "\\\\srv\\share"}],
              "parts": [{"disk": 0, "part": 1, "letter": "C", "size": 400000000000, "type": "Basic"}]}


def win_raw(payload):
    return "noise\n@@JSON\n" + json.dumps(payload) + "\n@@ENDJSON\n"


def test_windows_rows_and_drive_type():
    rows, summ = ci.build_machine(WIN, win_raw(WINPAYLOAD), None, [], {}, "T")
    d = {r["device"]: r for r in rows}
    assert summ["status"] == "verified"
    assert d["C:"]["kind"] == "filesystem" and d["C:"]["used"] == 300000000000 and d["C:"]["free"] == 100000000000
    assert d["G:"]["kind"] == "network-mount" and d["G:"]["size"] is None and d["G:"]["used"] is None
    assert d["disk0:part1"]["mount"] == "C:" and d["disk0"]["serial"] == "SN-W"


def test_windows_blank_letter_and_cloud_drive():
    p = json.loads(json.dumps(WINPAYLOAD))
    p["parts"].append({"disk": 0, "part": 2, "letter": " ", "size": 100, "type": "System"})
    p["logical"].append({"id": "H:", "label": "someone@example.com - Goo...", "fs": "FAT32",
                         "size": 16106127360, "free": 8000000000, "type": 3, "provider": None})
    rows, _ = ci.build_machine(WIN, win_raw(p), None, [], {}, "T")
    d = {r["device"]: r for r in rows}
    assert d["disk0:part2"]["mount"] is None
    assert d["H:"]["kind"] == "cloud-drive" and "not a local disk" in d["H:"]["note"]
    assert d["C:"]["kind"] == "filesystem"


def test_windows_section_error_is_partial():
    p = dict(WINPAYLOAD, errors={"parts": "access denied"}, parts=None)
    prev = [ci.row("greywolf", "partition", "disk0:part9", source="parts", last_seen="OLD")]
    rows, summ = ci.build_machine(WIN, win_raw(p), None, prev, {}, "T")
    assert summ["status"] == "partial" and summ["sections"]["parts"] == "unknown"
    assert [r["device"] for r in rows if r["status"] == "stale"] == ["disk0:part9"]


# ------------------------------------------------------------------------ transport and refusal
def test_public_address_refused_and_no_command_sent():
    calls = []
    m = {"id": "x", "os": "linux", "route": {"kind": "ssh", "host": "root@8.8.8.8"}}
    with pytest.raises(ci.Unreadable, match="refused"):
        ci.fetch(m, run=lambda *a, **k: calls.append(a))
    assert calls == []
    for ok in ("10.20.0.51", "192.168.1.91", "100.112.232.94", "127.0.0.1"):
        ci.check_address("root@" + ok)


def test_alias_resolving_to_public_is_refused():
    def run(argv, **k):
        return subprocess.CompletedProcess(argv, 0, "user root\nhostname 93.184.216.34\n", "")
    with pytest.raises(ci.Unreadable, match="refused"):
        ci.resolve_alias("evil", run)


def test_route_none_is_unknown_with_reason():
    m = {"id": "r610", "os": "linux", "route": {"kind": "none", "reason": "VLAN 30"}}
    with pytest.raises(ci.Unreadable, match="VLAN 30"):
        ci.fetch(m)


def test_fetch_sends_script_as_bytes_without_crlf_and_maps_failures():
    seen = {}

    def run(argv, **k):
        if argv[:2] == ["ssh", "-G"]:
            return subprocess.CompletedProcess(argv, 0, b"hostname 10.20.0.50\n".decode(), "")
        seen["argv"], seen["input"] = argv, k.get("input")
        return subprocess.CompletedProcess(argv, 0, b"@@BEGIN now\r\n5\r\n@@END now rc=0\r\n", b"")
    out = ci.fetch(LINUX | {"route": {"kind": "ssh", "host": "overlord"}}, run=run)
    assert isinstance(seen["input"], bytes) and b"\r" not in seen["input"]
    assert seen["argv"][-1] == "sh -s" and "BatchMode=yes" in seen["argv"]
    assert "\r" not in out

    def fail(argv, **k):
        if argv[:2] == ["ssh", "-G"]:
            return subprocess.CompletedProcess(argv, 0, "hostname 10.20.0.50\n", "")
        return subprocess.CompletedProcess(argv, 255, b"", b"ssh: connect to host x port 22: Connection timed out\n")
    with pytest.raises(ci.Unreadable, match="timed out"):
        ci.fetch(LINUX, run=fail)

    def slow(argv, **k):
        if argv[:2] == ["ssh", "-G"]:
            return subprocess.CompletedProcess(argv, 0, "hostname 10.20.0.50\n", "")
        raise subprocess.TimeoutExpired(argv, 1)
    with pytest.raises(ci.Unreadable, match="unknown, not down"):
        ci.fetch(LINUX, run=slow)


def test_via_route_nests_the_second_hop_and_never_embeds_a_key():
    argv = ci.ssh_via_argv({"kind": "ssh-via", "via": "overlord", "host": "root@10.20.0.52",
                            "via_key": "/root/.ssh/id_ed25519_auto"})
    assert argv[-2] == "overlord" and argv[-1].endswith("root@10.20.0.52 sh -s")
    targets = json.load(open(os.path.join(_NODE, "cluster_inventory_targets.json"), encoding="utf-8"))
    text = json.dumps(targets).lower()
    assert "password" not in text.replace("no key, password or token", "") and "begin" not in text


# -------------------------------------------------------------------- inventory and outputs
def test_targets_file_is_valid_and_names_every_machine():
    ms = ci.load_targets(ci.DEFAULT_TARGETS)
    assert {m["id"] for m in ms} == {"overlord", "r710-1", "r620", "r710-2", "r610", "greywolf", "surface", "msi"}
    for m in ms:
        if m["route"].get("kind") in ("ssh", "ssh-via"):
            ci.check_address(m["route"]["host"]) if m["route"]["host"].split("@")[-1][0].isdigit() else None


def test_make_inventory_end_to_end_and_previous_carry(tmp_path):
    ms = [LINUX, WIN, {"id": "r610", "os": "linux", "role": "lab", "route": {"kind": "none", "reason": "VLAN 30"}}]
    inv1 = ci.make_inventory(ms, {"overlord": linux_raw(), "greywolf": win_raw(WINPAYLOAD), "r610": None},
                             {"overlord": None, "greywolf": None, "r610": "VLAN 30"}, None, "2026-11-23T00:00:00Z")
    c = inv1["counts"]
    assert (c["machines"], c["verified"], c["partial"], c["unknown"]) == (3, 2, 0, 1)
    assert c["rows"] == len(inv1["rows"]) and c["rows_stale"] == 0
    p = tmp_path / "inventory.json"
    p.write_text(json.dumps(inv1), encoding="utf-8")
    # second run: overlord is now unreachable; its rows stay, as stale, with the OLD last_seen
    inv2 = ci.make_inventory(ms, {"overlord": None, "greywolf": win_raw(WINPAYLOAD), "r610": None},
                             {"overlord": "ssh timed out", "greywolf": None, "r610": "VLAN 30"}, str(p),
                             "2026-11-24T00:00:00Z")
    ov = [r for r in inv2["rows"] if r["machine"] == "overlord"]
    assert len(ov) > 15 and {r["status"] for r in ov} == {"stale"}
    assert {r["last_seen"] for r in ov} == {"2026-09-21T14:13:20Z"}
    s = {m["machine"]: m for m in inv2["machines"]}
    assert s["overlord"]["status"] == "unknown" and s["overlord"]["reason"] == "ssh timed out"
    assert s["overlord"]["last_seen"] == "2026-09-21T14:13:20Z"
    assert s["r610"]["rows"] == 1 and inv2["counts"]["unknown"] == 2
    # a placeholder is not a reading: the next run does not carry it as if it were data
    p.write_text(json.dumps(inv2), encoding="utf-8")
    prev, _ = ci.load_previous(str(p))
    assert "r610" not in prev


def test_outputs_csv_markdown_and_atomic_files(tmp_path):
    inv = ci.make_inventory([LINUX], {"overlord": linux_raw()}, {"overlord": None}, None, "2026-11-23T00:00:00Z")
    paths = ci.write_outputs(inv, str(tmp_path))
    assert sorted(os.path.basename(p) for p in paths) == ["INVENTORY.md", "inventory.csv", "inventory.json"]
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    header = open(tmp_path / "inventory.csv", encoding="utf-8").readline().strip().split(",")
    assert header[:3] == ["machine", "kind", "device"] and "last_seen" in header and "used" in header
    md = open(tmp_path / "INVENTORY.md", encoding="utf-8").read()
    assert "overlord" in md and "unknown" in md and "never that it is empty" in md
    data = json.loads(open(tmp_path / "inventory.json", encoding="utf-8").read())
    assert data["schema"] == "cluster-inventory-1" and len(data["rows"]) == len(inv["rows"])


def test_cli_render_from_raw_dir(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "overlord.raw").write_text(linux_raw(), encoding="utf-8")
    tf = tmp_path / "t.json"
    tf.write_text(json.dumps({"schema": "cluster-inventory-targets-1", "machines": [LINUX, dict(LINUX, id="b")]}),
                  encoding="utf-8")
    rc = ci.main(["render", "--targets", str(tf), "--raw-dir", str(raw), "--out", str(tmp_path / "o")])
    assert rc == 0
    d = json.loads((tmp_path / "o" / "inventory.json").read_text(encoding="utf-8"))
    st = {m["machine"]: m for m in d["machines"]}
    assert st["overlord"]["status"] == "verified" and st["b"]["status"] == "unknown"
    assert st["b"]["reason"] == "no recorded raw answer"
    assert ci.main(["collect", "--targets", str(tf), "--only", "nope"]) == 2


def test_stdlib_only_and_no_network_calls():
    src = open(os.path.join(_NODE, "cluster_inventory.py"), encoding="utf-8").read()
    for bad in ("import requests", "urllib", "http.client", "socket", "boto", "openai", "anthropic"):
        assert bad not in src, bad
