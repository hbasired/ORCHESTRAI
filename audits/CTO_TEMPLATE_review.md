# CTO checkpoint review (canonical template — sibling of tasks/CTO_REVIEW_TEMPLATE.md)

See [tasks/CTO_REVIEW_TEMPLATE.md](../tasks/CTO_REVIEW_TEMPLATE.md) for the full template shape. This file is a convenience copy in the same directory as the live `audits/CTO_<N>_review.md` outputs so anyone browsing `audits/` can see the expected shape.

Use `bash scripts/cto-review.sh` to produce the live file (requires `claude` CLI on PATH; spawns a fresh Claude Code subprocess with the `cto-reviewer` skill). Do not edit this template directly.

Companion file: each `audits/CTO_<N>_review.md` is paired with `audits/CTO_<N>_remediation_map.json`, which `scripts/generate-remediation-tasks.sh` parses to route future-task remediations to upcoming task docs as acceptance criteria.

Example `remediation_map.json` shape:

```json
{
  "remediations": [
    {"description": "Add ML-DSA signature verification path to A2A peer revocation handler", "target_stage": "14"},
    {"description": "Backfill model cards for Stage 4 transformer weights with Annex IV training-data attribution", "target_stage": "19"}
  ]
}
```
