# VDA 5050 JSON schemas — provenance

These are the **official VDA 5050 JSON schemas**, vendored verbatim from the upstream reference repository:

- Source: https://github.com/VDA5050/VDA5050 (`json_schemas/`), git **tag `2.1.0`** (VDA 5050 **v2.1.0**, Jan 2025).
  NOTE: the repo's `main` branch is **v3.0.0** (e.g. `state` uses `powerSupply` there vs `batteryState` in 2.1.0), so
  these were fetched from the pinned `2.1.0` tag — NOT `main` — to match the Stage-16 acceptance criterion.
- License: **MIT** (upstream repo) — redistribution with this provenance note.
- Fetched: 2026-06-20 (Stage 16), from the `2.1.0` tag.

Files (upstream `.schema` → stored as `.json` so `datamodel-code-generator` + `jsonschema` recognise them):
`order.json`, `state.json`, `connection.json`, `instantActions.json`, `factsheet.json`, `visualization.json`
(the `responses` / `zoneSet` schemas are not used by the master controller this stage).

**Do not hand-edit** — re-fetch from upstream to update. The `models/` package is generated from these by
`datamodel-code-generator` (see `../compile_models.sh`); `backend/tests/integrations/test_vda5050_schema.py`
validates canned payloads against them with `jsonschema`.
