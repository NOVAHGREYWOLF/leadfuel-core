---
name: new-project
description: Start a project the way the owner wants it started, with the sidebar groups, the two pages and the plan files in place and one router (never more) opened for it. Use when the conductor has queued tasks that belong to a project with no live router, or when the owner says "new project".
---

# new-project

A project is one objective with one task list and **one router**. The conductor runs this; a router never starts a project.

## 1. Name it
A short slug (`leadfuel-way`, `reports`) and a one-line goal. Check that no live router already holds it: `list_sessions` with `group: "ROUTER"` and a small `limit`, and read the titles. If one does, hand it the tasks and stop.

## 2. Sidebar groups
Nothing is ever ungrouped. Check with `list_groups` and create what is missing with `create_group`:
- **CONDUCTOR** (one session) and **ROUTER** (one router per project). Neither is a lane for desks (owner, 2026-10-02): the work itself goes in the lane its files belong to.
- **One group per desk lane** the project's tasks touch. The lane list is the owner's desk list; if a lane you need is not in it, ask on the Router desk page rather than inventing one.
A group is a shelf, not an address: route to a session by its full name, never to a group.

## 3. The two pages
- **Router desk**: questions for the owner, one card each, with options and a default.
- **Conductor desk**: the complete task list, grouped by lane.
Both are artifact pages whose URLs are in the board doc `router/desks`, built by their own sessions. Check they exist; if either does not, say so to the owner and stop short of inventing a stand-in.

## 4. Plan files
In the project's repo, under `.conductor/` (public repo: ids, titles, status, PR numbers only): `project.json` (slug, goal, lanes, budgets) and `tasks.json` (task id, lane, title, effort, envelope, optional `model_pin`, done-criteria). The Conductor desk page is the owner's view of the same list; the files are what the router reads. If the project already has a plan, read it and add to it.

## 5. One router
Open exactly one session for the project, titled `ROUTER #N · <project>`, filed in the ROUTER group, on Sonnet. How a session is opened is in `leadfuel-way:router`, "Opening a desk" (`start_session` if the tool exists, else a `spawn_task` chip the owner clicks, then title, group and model). Its brief names the project, the queued task ids, the true source of the instruction, and tells it to read `leadfuel-way:way` and `leadfuel-way:router`.

## 6. Confirm
Re-read the router group: the new router is there, titled, on the model you set. Tell the owner in one line what exists. A step you could not complete goes in the answer as not done.
