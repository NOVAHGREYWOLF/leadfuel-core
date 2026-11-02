# Fixed-question AI-answer check (WEB-H2)

Asks 10 fixed questions to outside AI assistants and records whether the expected names
appear. Questions are in `questions.json`, status DRAFT (drafted from the web portfolio
report; the report never wrote the ten down). Edit them and set `status` to `APPROVED`.

Law 9: a live run sends text off this machine. Default is dry-run (no network). Live refuses
unless a local approval file exists with the Router desk card id that approved it. Default path
`~/.leadfuel/ai_visibility/approval.json` (outside the repo; override with `AI_VISIBILITY_HOME`):

    {"approved": true, "card_id": "q123", "assistants": ["name"]}

No adapters ship. After the card is answered, register one in `ADAPTERS` in `check.py`
(name -> function(question) -> answer). Until then even an approved live run sends nothing.
Results are stored under `~/.leadfuel/ai_visibility/runs/` (never in the repo; answers may be long).

    python scripts/ai_visibility/check.py            # dry run
    python scripts/ai_visibility/check.py --store    # dry run, saved
    python scripts/ai_visibility/check.py --history
