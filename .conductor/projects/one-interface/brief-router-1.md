# SUPERSEDED: no separate router. The estate router (ROUTER #25 local_447575ed) runs this project.
Owner, ~05:39Z 10-07: "send it to router. this shouldnt be a new router. this should tell router
what we are doing". The sources, the task list and "First moves" below still apply to the estate
router, apart from step 1's handover, which is now moot.

# Brief: ROUTER #1 · one-interface (from CONDUCTOR 017 local_51008c82, 2026-10-07)

Public repo: ids and titles only. The full spec is on the Conductor desk, task SURFACE CC-GAME-SHELL.

You are the one router for project `one-interface`. Invoke `leadfuel-way:way`, then
`leadfuel-way:router`. Title yourself `ROUTER #1 · one-interface`, file yourself in the ROUTER
group, and check that your model is Sonnet. Your worktree is this one
(`.claude/worktrees/router-one-interface-1`, branch `claude/router-one-interface-1`).

## True source (read it yourself)
- The owner typed in SURFACE command center nav button (local_9ec7acd5-fe31-4f8b-af7f-0610e6348c35),
  ~04:55Z 10-07: "yes thats right, start the one-interface project", after "it should all be one
  congruent interface. easy to navigate like a video game". Find both with
  `search_session_transcripts`.
- Earlier the same night, in ROUTER #24 (local_17705746): "eventually this will be the home page when
  you login" and the RPG direction ("Think Final Fantasy...").
- The spec as filed: Conductor desk https://claude.ai/artifact/MKAx49RAskZ3cV7f2EkDMF, `desks/surface`,
  task `CC-GAME-SHELL`, pick `SURFACE~CC-GAME-SHELL` (rank 222).
- The SURFACE desk's notes: `.conductor/desks/handoffs/SURFACE-command-center-nav-001.md` on
  `claude/zealous-heisenberg-tlqil3`, and its review page `Fb9uKC6G4Z93nMMRqnqDBo`.

## What is queued
Everything in `tasks.json` next to this file: the umbrella plus 20 tasks the owner had already
queued over 10-02..10-06. They are now this project's, not the estate router's. Several are
HELD (close-first, Fable pins, merge order). The pick notes say which, so read each one.

## First moves
1. **Find who already holds what.** Search transcripts for each task id. Known: SURFACE
   CC-ROUTE-MOVE 1/1 local_e137f345 (no PR), ONE-PLACE-SHELL 1/1 local_5c44a1ab (at cap; handoff on
   hub `one-place-shell`), ATLAS-in-command-center (PR #730 owed), hub #776 `/command` (open).
   Ask ROUTER #25 (local_447575ed) to hand over its roster rows for these. #25 keeps the merge train.
2. **The first new desk:** the DESIGN mock-up of the one interface (ONE-PLACE-DESIGN, pinned to
   Fable). It builds on the LeadFuel Command design `P2My4JdZjnEUtZDFer3ZBs` and Atlas Live v11
   `6LEvF7K9u9qnSxh68VWsfA`, for the owner to react to before anyone builds. ROUTER #24 proposed
   this; the owner did not say it.
3. **Cards** go on the estate Router desk, titled with the prefix `one-interface:`.

## Rules
Merging to hub main deploys. PRs land through the estate merge train, on green, inside the CI
hold. Nothing leaves the machine without the owner. Report to the live CONDUCTOR, named in the Build
Board `router/current` field `conductor`.
