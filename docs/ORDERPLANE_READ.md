# ARMS fold-s-orderplane: the order-plane switch read kit

Kit: `scripts/orderplane_read/orderplane_read.py`, tests `tests/test_orderplane_read.py`. Modelled on the SENSORS-4 read-only pass: `--target` mandatory, plan by default, `--plan` with `--run` refused.

Reads names and state words only (`on`, `off`, `unset`, `other`; tokens `present` or `absent`). Switches: each arm's `SPOKE_WORKER_ENABLED` (the pull loop also needs a token), the hub's `RUNNER_ENABLED`, `RUNNER_REQUIRE_APPROVAL`, `SPOKE_ENFORCE_CONFORMANCE`, `SPOKE_ENFORCE_LIVENESS`, and the connector's `RUNNER_ENABLED`. A service it cannot read is `unknown`, never `off`.

Plan (connects to nothing): `python scripts/orderplane_read/orderplane_read.py --target railway --plan`

Run (production read, not done): needs the owner's typed yes in the ARMS "land the backlog" desk chat, then `--target railway --run --typed-yes-ref "<where he typed it>"`.

Unverified: the Railway service names other than the hub (`NovaHub`). Confirm with `railway status` (names only) first; a wrong name gives `unknown`.

Not built here: the second half of the queue item, "one order runs hub to arm and back". That needs the switches on and is the ARMS desk's.
