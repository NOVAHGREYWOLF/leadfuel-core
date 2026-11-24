"""WATCH: does the hub's spend-approval mail land in the Inbox?  READ-ONLY, sends nothing (Law 9).

Background (webchat-6): the mail "Approve spend: N asks" from the hub sender was filed by a mailbox
rule into a folder with hundreds of unread, so spend requests went unanswered. The rule lives in the
owner's mailbox, outside this repo; this check is the half that can be kept here. It notices the
next time such a mail is not in the Inbox.

  python watch/approval_mail_check.py --evidence mail.json

Evidence (JSON list, ids and folders only, gathered by whoever can search the mailbox):
  [{"id": "...", "sender": "...", "subject": "...", "folder": "Inbox"}, ...]
A message counts as approval mail when its sender is APPROVAL_SENDER and its subject starts with
APPROVAL_SUBJECT. Only those are judged.

PASS     at least one approval mail seen and every one has folder "Inbox".
FAIL     any approval mail has a folder that is not the Inbox.
UNKNOWN  no approval mail in the evidence, or a matching message with no folder recorded. A search
         that cannot see the folder or the mail does not prove the rule is fixed.
Exit 0 PASS, 1 FAIL, 2 UNKNOWN. Stdlib only.
"""
import argparse
import json
import sys

APPROVAL_SENDER = "hello@mail.leadfuel.cloud"
APPROVAL_SUBJECT = "approve spend"


def is_approval_mail(msg):
    if not isinstance(msg, dict):
        return False
    sender = str(msg.get("sender") or "").strip().lower()
    subject = str(msg.get("subject") or "").strip().lower()
    return sender == APPROVAL_SENDER and subject.startswith(APPROVAL_SUBJECT)


def judge(messages):
    """Return (verdict, reasons) for a list of message dicts."""
    if not isinstance(messages, list):
        return "UNKNOWN", ["evidence is not a list of messages"]
    mails = [m for m in messages if is_approval_mail(m)]
    if not mails:
        return "UNKNOWN", ["no approval mail in the evidence, so nothing was checked"]
    misfiled, unseen = [], []
    for m in mails:
        folder = m.get("folder")
        if not isinstance(folder, str) or not folder.strip():
            unseen.append("%s: folder not recorded" % m.get("id", "?"))
        elif folder.strip().lower() != "inbox":
            misfiled.append("%s: in %r, not Inbox" % (m.get("id", "?"), folder))
    if misfiled:
        return "FAIL", misfiled + unseen
    if unseen:
        return "UNKNOWN", unseen
    return "PASS", ["%d approval mail(s), all in the Inbox" % len(mails)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", required=True)
    args = ap.parse_args(argv)
    try:
        with open(args.evidence, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print("UNKNOWN: evidence unreadable (%s)" % type(exc).__name__)
        return 2
    verdict, reasons = judge(data)
    print("%s: %s" % (verdict, "; ".join(reasons)))
    return {"PASS": 0, "FAIL": 1}.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
