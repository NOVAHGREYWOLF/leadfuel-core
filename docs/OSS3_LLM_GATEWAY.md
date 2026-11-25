# oss-3: llama-swap with LiteLLM in front (wrapper, nothing installed)

Draft. Nothing is downloaded, started or enabled by anything here. No socket is opened by the guard.

## What is in the box
- `node/gateway/llama-swap.yaml`: two placeholder models (`local-small`, `local-code`), model files named as placeholders; no model is fetched from a URL.
- `node/gateway/litellm_config.yaml`: one OpenAI-compatible route per model, `api_base` on `overlord` (private), `api_key: none`, telemetry off, no retries, no fallback list, no callback.
- `node/gateway_guard.py` plus `tests/test_gateway_guard.py` (24 tests): fails on any cloud provider prefix, public `api_base`, missing `api_base`, secret reference, fallback key (local-to-local too), callback, telemetry on, or a model command that downloads. A missing file fails, it never passes.

The address of the one model service lives in `node/model_service.json` (PR 113, open). This change does not edit it and does not depend on it. When W09 lands and the owner enables `overlord-gpu`, the two files must agree on the port (8080 here, llama-swap's default; a proposal until W09).

## Why a cloud route is not a fallback
A cloud route is a named decision behind the approval gate (Law 9). The guard makes a pasted vendor entry a red test, so it cannot arrive as a convenience.

## Not verified
LiteLLM's licence: the part-15 record says it reports mixed licences, so read its licence file before adopting. The `openai/<name>` plus `api_base` form and the `telemetry: false` key are from memory of the LiteLLM docs, not tested against a running proxy. Model file names are placeholders.

## OWNER-STEP
After P12 and W09 (CT 105 on overlord) exist: type yes to the GPU container and to the install download (llama-swap, LiteLLM), then run `python node/gateway_guard.py` and `python node/model_service.py probe overlord-gpu`.
