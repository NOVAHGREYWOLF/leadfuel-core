#!/usr/bin/env python
"""Post a card: build one valid Router desk `questions` document, so the session that needs the owner writes it itself.

    python post_card.py --n 9124 --asker "NODE · full system automation part · 4" --asker-session local_<uuid> \\
        --title "Should the Stop hook refuse ...?" --say "Make the Stop hook refuse ..." \\
        --why "..." --check "verified: ..." --option "A=Yes, refuse (recommended)" --option "B=No" \\
        --default A --default-reason "..." --out card.json

The session then writes the file with ArtifactData `set` (`collection` questions, `doc_id` q<n>, no `if_version`: a
set on an id that already exists is refused, so a clash on n is safe; run it again with n+1). The wake pass carries
the owner's click back to `asker_session`, so nothing is typed in chat, and nothing waits on a chip or on
AskUserQuestion.

Rules this script holds (owner, 2026-10-30, "every card has Something else"): option X, "None of these: something
else (write it in the note)", is always present; the default is never X; every card carries `check` (what was
verified, and by whom, or `unverified:`) and a `default_reason`. A step card (`--kind step`, the owner does a thing
and says done) may carry `--guide` lines and `--link LABEL=URL`. The fields are those of the live cards (q9013,
q9123); `answer` and `routed` start null. Nothing here touches the network or the page: it writes a file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SID = re.compile(r"local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
X_LABEL = "None of these: something else (write it in the note)"
KINDS = ("choice", "step")
MAX_TITLE = 140
MAX_OPTIONS = 6  # A..F, with X on top


class CardError(ValueError):
    """The card cannot be built as asked; the message says which field."""


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def build_card(n, asker, asker_session, title, say, why, check, options, default, default_reason, kind="choice",
               effects=None, guide=None, links=None, posted=None, now=None) -> dict:
    """The document for `questions/q<n>`. options is [(key, label)] without X; X is added (or kept if given)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise CardError("n must be a positive integer")
    if kind not in KINDS:
        raise CardError(f"kind must be one of {KINDS}")
    if not SID.fullmatch(str(asker_session or "")):
        raise CardError("asker_session must be your own full session id, local_<uuid>: the click is sent back to it")
    asker, title, say, why, check, default_reason = (_clean(v) for v in (asker, title, say, why, check, default_reason))
    for name, value in (("asker", asker), ("title", title), ("say", say), ("why", why), ("check", check),
                        ("default_reason", default_reason)):
        if not value:
            raise CardError(f"{name} is required")
    if len(title) > MAX_TITLE:
        raise CardError(f"title is {len(title)} characters; the page shows {MAX_TITLE} at most")
    opts, seen_keys, x_label = [], set(), X_LABEL
    for key, label in options:
        key, label = _clean(key).upper(), _clean(label)
        if not re.fullmatch(r"[A-Z]", key) or not label:
            raise CardError(f"option {key!r}: a key is one letter and a label is required")
        if key in seen_keys:
            raise CardError(f"option {key} is given twice")
        seen_keys.add(key)
        if key == "X":
            x_label = label
        else:
            opts.append({"key": key, "label": label})
    if not 2 <= len(opts) <= MAX_OPTIONS:
        raise CardError(f"a card has 2 to {MAX_OPTIONS} real options besides X, not {len(opts)}")
    default = _clean(default).upper()
    if default == "X" or default not in {o["key"] for o in opts}:
        raise CardError("default must be one of the real options, never X")
    opts.append({"key": "X", "label": x_label})
    stamp = (now or datetime.now().astimezone()).strftime("%Y-%m-%d")
    card = {"id": f"q{n}", "n": n, "kind": kind, "title": title, "asker": asker, "asker_session": asker_session,
            "posted": posted or f"{stamp} {asker}", "why": why,
            "plain": {"say": say}, "check": check, "options": opts, "default": default,
            "default_reason": default_reason, "answer": None, "routed": None}
    if effects:
        card["plain"]["effects"] = {_clean(k).upper(): _clean(v) for k, v in dict(effects).items()}
    if guide:
        if kind != "step":
            raise CardError("guide lines belong on a step card (--kind step)")
        card["guide"] = [_clean(g) for g in guide if _clean(g)]
    if links:
        card["links"] = [{"label": _clean(lab), "url": _clean(url)} for lab, url in links]
    return card


def _pairs(items, flag):
    out = []
    for item in items or []:
        key, sep, rest = str(item).partition("=")
        if not sep:
            raise CardError(f"{flag} wants KEY=text, got {item!r}")
        out.append((key, rest))
    return out


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", required=True, type=int, help="card number: one above the highest `n` in the collection")
    ap.add_argument("--asker", required=True, help="your session title, e.g. `NODE · full system automation part · 4`")
    ap.add_argument("--asker-session", required=True, help="your own session id (get_session self): the answer comes back here")
    ap.add_argument("--title", required=True)
    ap.add_argument("--say", required=True, help="the one plain sentence the owner reads")
    ap.add_argument("--why", required=True)
    ap.add_argument("--check", required=True, help="what was verified, by whom; or `unverified: ...`")
    ap.add_argument("--option", action="append", default=[], help="KEY=label, repeated; X is added for you")
    ap.add_argument("--effect", action="append", default=[], help="KEY=what that choice does, repeated (optional)")
    ap.add_argument("--default", required=True)
    ap.add_argument("--default-reason", required=True)
    ap.add_argument("--kind", default="choice", choices=KINDS)
    ap.add_argument("--guide", action="append", default=[], help="a step card's numbered instruction line, repeated")
    ap.add_argument("--link", action="append", default=[], help="LABEL=URL, repeated (optional)")
    ap.add_argument("--out", required=True, help="the file to write; hand it to ArtifactData set as file_path")
    args = ap.parse_args(argv)
    try:
        card = build_card(args.n, args.asker, args.asker_session, args.title, args.say, args.why, args.check,
                          _pairs(args.option, "--option"), args.default, args.default_reason, kind=args.kind,
                          effects=dict(_pairs(args.effect, "--effect")), guide=args.guide,
                          links=_pairs(args.link, "--link"))
    except CardError as exc:
        print(f"CARD-NOT-BUILT: {exc}")
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"CARD q{card['n']} written to {out}; now ArtifactData set, collection questions, doc_id q{card['n']}, "
          f"file_path that file, no if_version (refused on a clash: run again with n={card['n'] + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
