# Likeness licensing: design record

**STATUS: NOT FOR BUILD. PARKED BEHIND COUNSEL.** No code, schema, connector, offer type or
export path may be built from this page until counsel has signed the likeness license and the
compliance memos (document set tab L3). This page is a design record, not legal advice. Nothing
here has been reviewed by a lawyer.

Task: webchat-13 (lane LAB, kind scope). Origin: the owner's idea in the Gamifying chat,
2026-10-11 ("we will be buying each others likeness"). Law 9 applies to every part of it: a
likeness leaving the machine is a transmission and needs the owner's approval per use.

## What was agreed

Likeness licensing is a **fourth deal type** in the Market spoke, on the same approval spine as
the other three. A person licenses their likeness to a title, at one of three tiers:

| Tier | What is licensed | How it is delivered | Unlocked |
|---|---|---|---|
| Appearance | avatar and display name | exported with a provenance manifest tied to the license id | level 6 |
| Voice | a spoken voice model | served under the license, never exported | level 7, after a consented recording session |
| Behavior | the twin acting as the person inside the title | served through a license-scoped Self, metered and logged | level 8 |

Fixed controls, all from the source specs:

- **Consent per use.** Opt in per tier and per title. Nothing is licensable by default. The
  person previews the title, role, scope and sample lines or renders before approving.
- **Kill switch and revocation.** The person can revoke future use at any time. Voice and
  behavior serving stops at once; appearance exports are not re-issued.
- **Platform prohibited uses that cannot be lowered:** sexual content, political persuasion,
  depiction with or directed at minors, deception about identity, use outside the licensed
  title, training any model on the asset.
- **Minors are never licensable.**
- **Served, not exported,** for voice and behavior. The licensee never receives weights or data.
- A person's real face and voice data stay `local_only` (see
  `F:/Leadfuel/home-node/27-Store-Privacy-Tiers.md`,
  `characters` row); only a served or provenance-marked output may leave, and only after approval.

## Where the full design lives

I checked: the design is already written in the NovahOS Document Set (2026-10-11), under
`F:\Leadfuel\Important Documents\03 NovahOS Document Set (2026-10-11)\`:

- `tab-32-k7-market-brief.md`: the Market spoke, item 8 "Likeness" is the fourth deal type.
- `tab-10-p2-character-maker-and-likeness.md`: the character object, tiers, export and runtime.
- `tab-11-p3-likeness-marketplace-case.md`: the business case, risks and controls.
- `tab-35-l3-likeness-license-and-compliance-memos.md`: the outline handed to counsel.

The planner's worry was whether SPOKES.md covers this. I found no SPOKES.md file; the Market
brief (tab 32) is the spoke spec and it does cover likeness. The game design page
(`GAME-DESIGN.md`, part 13 handoff folder) lists likeness as out of scope for the game.

## Questions only counsel can answer (from L3, not answered here)

1. Do California's 2024 digital replica statutes (AB 2602, AB 1836) need a separate consent per
   use, or representation, for this kind of license?
2. Is the platform a data broker for likeness deals, and does the Delete Act apply?
3. What notice of financial incentive, tax and payout treatment applies to likeness fees?
4. Is behavior-tier output, said in a person's voice, a different risk class (defamation,
   endorsement) from appearance, and what must the scope clause say?
5. Which other states and the EU AI Act disclosure rules bind a title that ships abroad?

## Gate for lifting the park

All of: counsel signs L3; the owner decides in a Router desk card; the Market spoke exists in
credits (phase 3); a named desk owns the build. Until then this item stays a scope record.

## Visible in the NovahOS shell when it is built

A "Likeness" setting inside the Market room: per-tier opt-in switches, the list of active
licenses with a revoke button on each, and an alarm entry when a license is used. Not a web
chat only. Not built; recorded so the build brief starts from it.

## Link owed

The Market brief (tab 32) should carry one line pointing here:
`Likeness licensing is parked behind counsel: see leadfuel-core docs/LIKENESS_LICENSING.md.`
That file is outside this repo and outside this task's lane, so it is not edited here.
