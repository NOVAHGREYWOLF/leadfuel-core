# Handoff: WATCH · RESEND-CHECK 1/1 (desk), 2026-10-06 ~22:25Z

Session: this desk (WATCH group). Opened by ROUTER #24 (local_17705746). Source: Router desk q313 = B (21:19:54Z). No PR. Ids, titles and status only.

## Done (verified by me)
- Read run f6a9997a's transcript (local_f6a9997a, "WATCH · etg.ai Resend verification"): task etgai-resend-verification, to read the Resend domain status via the API, re-trigger before 72h, diagnose after. It stopped at its first command, no output.
- Public DNS, read-only, no key: the DKIM TXT, SPF TXT and MX for the send subdomain, the click-tracking CNAME and DMARC each resolve to exactly one record on two public resolvers and on both authoritative nameservers. No duplicates; quoting parses. DMARC policy unchanged (none).
- The live DKIM key matches the key the SENSORS setup session (local_97347357) recorded on 2026-09-24 (transcript search on three fragments; not byte-compared against the API).

## Unknown
- Resend's own domain status. No public source shows it; no session has read it since 2026-09-24. It needs the API with the key or the Resend dashboard. Not attempted.

## Owed
- ASK sent to ROUTER #24: how to read Resend's status (owner dashboard, keyed read in a desk with the owner present, or close as DNS-clean). Router archives f6a9997a and this desk per the answer.
