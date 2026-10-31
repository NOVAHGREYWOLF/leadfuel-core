---
name: new-project
description: Start a project the way the owner wants it started, with the sidebar groups, the two pages and the plan files in place and one router (never more) opened for it. Use when the conductor has queued tasks that belong to a project with no live router, when the owner says "new project", or (step 2 only) when a router finds a project it holds has no sidebar group yet.
---

# new-project

A project is one objective with one task list and **one router**. The conductor runs this; a router never starts a project.

## 1. Name it
A short slug (`leadfuel-way`, `reports`), a one-line goal, and **the project's name as the owner says it** (for example `reports`, `world intel`, `one-interface`, `photo store`): that name is the project's sidebar group. It is never ROUTER, CONDUCTOR or the name of a desk lane. Check that no live router already holds the project: `list_sessions` with `group: "ROUTER"` and a small `limit`, and read the titles. If one does, hand it the tasks and stop.

## 2. Sidebar groups
Nothing is ever ungrouped. The owner, 2026-10-07: "The sidebar group becomes the master project". Check with `list_groups` and create what is missing with `create_group`:
- **CONDUCTOR** (one session) and **ROUTER** (one router per project). These are tiers and keep their groups; neither is a lane or a project.
- **The project's own group**, named as in step 1. If `list_groups` already has a group of that name (ignoring case), use it; otherwise `create_group` with that name. Every desk of the project is filed here, whatever its lane; the lane is in each desk's title (`LANE · <project> part · n`, `leadfuel-way:way` section 2a).
- **This step is the one place a project group is made.** A router holding a project that has no group yet (a project started before 0.1.8) runs this step, and only this step, for that project before it files the project's next desk, and records the group in that project's `project.json` (step 4) where the project keeps one. Nobody files a desk in its lane's group instead, and nobody leaves one ungrouped while the group is missing.
- **No new lane groups.** The existing lane groups stay, holding the sessions that have not migrated. Do not delete them and do not empty them: sessions leave them one at a time, never in bulk, by the owner or by each session itself on its own first turn.
A group is a shelf, not an address: route to a session by its full name, never to a group.

## 3. The six required documents
Every project has all six from day one (owner, 2026-10-30, card q763 A):
1. **Router desk page**: the project's own page of questions for the owner, one card each, with options and a default. Built from the template `.conductor/templates/router-desk.html`; its address goes on the board doc `router/desks`. Until a project has its own page, its cards go on the shared Router desk page, and that is recorded as the page in `project.json`.
2. **Project ledger page**: the project's running record (what is done, open, owed).
3. **`project.json`** (step 4).
4. **`tasks.json`** (step 4).
5. **Owner-steps sheet**: the steps only the owner can take, each with a done mark.
6. **Roster**: who holds what (`router/roster` on the Build Board, with the project's sessions and agents).
The **Conductor desk** (the complete task list, grouped by lane) is estate-wide and is not one of the six. The page URLs are in the board doc `router/desks`, built by their own sessions. **Check all six exist; a missing one is made now, or carded to the owner if only the owner can make it. Do not open the router until the check passes, and never invent a stand-in.**

## 4. Plan files
In the project's repo, under `.conductor/` (public repo: ids, titles, status, PR numbers only): `project.json` (slug, goal, `group` (the project's sidebar group name, exactly as created in step 2), lanes, budgets) and `tasks.json` (task id, lane, title, effort, envelope, optional `model_pin`, done-criteria). The Conductor desk page is the owner's view of the same list; the files are what the router reads. If the project already has a plan, read it and add to it.

## 5. One router
Run the check in step 3 again first: all six documents exist. Then open exactly one session for the project, titled `ROUTER #N · <project>`, filed in the ROUTER group, on Sonnet. How a session is opened is in `leadfuel-way:router`, "Opening a desk" (`start_session` if the tool exists, else a launch slot with no click (`leadfuel-way:launch`; a slot session cannot be filed in the ROUTER group, so title it and record it), else a `spawn_task` chip the owner clicks, then title, group and model). Its brief names the project, the queued task ids, the true source of the instruction, and tells it to read `leadfuel-way:way` and `leadfuel-way:router`.

## 6. Confirm
Re-read the router group: the new router is there, titled, on the model you set. Re-read `list_groups`: the project's group is there. Tell the owner in one line what exists. A step you could not complete goes in the answer as not done.

<!-- WAY-PANES-1 begin -->
## 7. Panes (WAY-PANES-1)
The project's Router desk page (document 1 in step 3) is built from the template with its Home | Code switch and its Build and Desk panes (`leadfuel-way:way`, section 8). Step 3's check includes that: a page without the switch and both panes is out of date, so rebuild it from the current template. Fill the project config (`name`, `slug`, `prefix`, `ledgerUrl`, `conductorUrl`, `routerTitle`, `buildUrl`) and seed the `build` collection, or leave it empty and say so.
<!-- WAY-PANES-1 end -->
