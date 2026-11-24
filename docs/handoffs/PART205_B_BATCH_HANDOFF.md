# Part 205 B-batch handoff (SURFACE desk, 2026-11-23 PT)

Branch `surface/part205-b-batch`. Done: see docs/PART205_B_BATCH.md.

Remaining ids, in order of use:
1. **redline-5**: the table of 26 owner questions, 22 Law 9 paths and 30 steps. Inputs are
   `F:\Claude Sessions\handoff\one-interface-redline-audit\` (OWNER-QUESTIONS.md, LAW9.md, STEPS.md). Needs read-only code
   checks on hub, echo and lucid main; the desk's git guard refused git outside its own worktree, so use fresh
   `git worktree` checkouts or the Grep tool on a current checkout, and write the SHA read per row.
2. **mail2-30**: one-page have/partly/missing table for the 14 bullets of the five-step AI platform list, with queue ids.
3. **chats-16**: the one page of four sites (what each shows, should show, links). Draft, unpublished.
4. **machines-2**: owner step only, unless the Surface is reachable by ssh (user milto); check ahead-count first.
5. Wire `brand/novahos-brand.json` into the app (DESIGN lane) and add the pointer sentence to GAME-DESIGN.md section 0.
