# VAULT · one-interface part · 90 handoff (VAULT~PLATFORM-COUNTS-AGGREGATE-MODULE). Ids only. 2026-10-19.

Source: owner card q603 A (Router desk questions/q603); conflict q605 C, q606 open. Host ROUTER #83 local_4b0acbb8. Drafts only, nothing lands.

## Done
- hub #951 (vault/counts-aggregate-wall, head 672248eb, base vault/866-w2-w3 @ 60cee86c): platform_counts.py (floor 3), tests/test_platform_counts.py (25), wall W1/W2 recognise the module by name (tests/_admin_wall.py, _admin_wall_w2.py, test_admin_wall.py +9). Gates 14/16 green, 2 skipped. Wall file: same 4 pre-existing failures as pristine 60cee86c (W1 new reads, W2 canary, W2 reads, W2 case B); none introduced.

## In progress
- hub #952 (vault/counts-aggregate-rail, head 5b19c9ca, base surface/q581-counts-only @ 0252e899). Worktree F:\Leadfuel\repos\novahub\.claude\worktrees\vault-counts-aggregate.
- 4 red in tests/test_command_views.py, test_command_rail.py, test_command_sources.py:
  1. test_the_bare_admin_counts_the_platform_and_lists_no_row: TypeError None >= int in a platform consumer (withheld count); find it, render via platform_counts.say.
  2. test_the_bare_admin_memory_feed_counts_and_returns_no_row_or_label: key set pin; feed now adds floor, withheld.
  3. test_the_module_names_no_column_that_holds_a_persons_text: regex pin on `where.append(UserMemory.account_email == em)`; account scope now in the list literal. Check what the pin guards before touching it.
  4. test_the_recent_read_is_two_statements_however_many_rows_there_are: platform recent is now bucketed + totals counts.
- Then: consumers of withheld None in views/layers (embedding, door_in M1 when total None, glance, terrain/parsers/age/arrivals/travel with lag_withheld, pools), tests at floor for each, gates, and a combined-tree W2 measure (merge #951 + #952) to report which modules still read C tables for the bare admin.
- Known: dead platform `else` branch left in command_sources._holdings; extract('hour') on Postgres timestamptz unverified.
