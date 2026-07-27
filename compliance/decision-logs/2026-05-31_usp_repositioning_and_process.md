# ADR — USP repositioning, carry-forward gaps ledger, audit→fix loop, system-designer role (2026-05-31, run 2)

**Status**: accepted
**Stage**: cross-cutting (strategy + process)
**Author**: agentic-governance-engineer + system-designer personas (Claude session, 2026-05-31); operator-directed
**Related**: research/initial-research.md §12; research/system-explainer/index.html; audits/OPEN_GAPS_LEDGER.md
**KB updates**: KB_24 (new HLD/LLD), KB_README; CLAUDE.md §3/§6; SKILLS.md; new skills task-auditor + system-designer

---

## D1 — Reposition the USP beyond EU AI Act + PQC

**Context.** Operator: the USP must be substantial/fundamental/innovative, not just compliance + post-quantum
crypto; and the product must adopt competitors' strengths (digital twin, predictive maintenance, observability/
teleop/fleet-data-ops, orchestration-to-standards, evals/guardrails to Galileo depth, determinism/PLC heritage,
large-scale deployment) rather than being strong on one axis.

**Decision.** New USP (grounded in code + research §12): **the open, vendor-neutral control plane that runs
robots + machines + supply chain as ONE self-optimizing system — every decision simulated in a digital twin,
safety-gated, and cryptographically provable.** Three legs: breadth (cross-domain embodied coordination — our
`EmbodiedCoordinator`, the hardest leg, already built), foresight (simulate-before-act), trust (signed,
replayable provenance). EU AI Act + PQC are demoted to trust *features*. Each competitor strength becomes a
staged pillar (mapped in research §12.2, KB_24 §3, and the gaps ledger G-005..G-014).

**Why.** Compliance/crypto are necessary but not a product; the cross-domain + foresight + trust combination is
defensible and is something no surveyed competitor ships. Honest viability (told to operator): this is a
vendor-neutral integration/orchestration layer + OSS wedge → multi-vendor warehouse pilots → integration
partner/acquisition — NOT an incumbent rip-and-replace.

**Consequences.** PRD v2.2 records the repositioning; the new full-system explainer HTML communicates what/how/
why + honest viability; the roadmap must actually build the PLANNED pillars before parity can be claimed.

## D2 — Carry-forward gaps ledger (`audits/OPEN_GAPS_LEDGER.md`)

**Context.** Many audit findings cannot be fixed in the observing stage; their solution lands in a later stage.
They must not be lost.

**Decision.** A persistent, append-only ledger records each gap with a `target_stage`. Protocol: independent
audits + CTO reviews APPEND deferred gaps; `start-task.sh`/`/begin` SURFACE rows whose target ≤ the starting
stage so the implementer folds the fix into that stage's acceptance criteria; `close-task.sh` warns if rows
targeted at the closing stage remain OPEN. Seeded with the Stage 3 gates, the identity-review repair-dispatch
gap, the market-analysis "exposed fields", and the repositioning pillars (G-001..G-015).

**Why.** Exactly the operator's requirement: the system remembers earlier-observed gaps and fixes them when the
right stage arrives.

**Consequences.** `start-task.sh` surfacing of ledger rows is specified; wiring it into the script is a
follow-up (tracked). Today the ledger + protocol + audit/CTO append paths exist.

## D3 — Audit is not just a report: report → fixer → re-audit; auditor gets context

**Decision.** The independent `task-auditor` (a) is given the stage's implementation context (changed files,
task doc, KB_TASK_LOG entry, ADRs) by `independent-audit.sh`; (b) appends deferred gaps to the ledger; and (c)
its report is **handed to an implementer session that fixes the gaps**, then a fresh auditor re-audits — only a
PASS unblocks close. `independent-audit.sh` prints the audit→fix handoff. (See ADR 2026-05-31_independent_audit
for the independence rationale.)

**Why.** Operator: the auditor "should not only report, it should be given to the actual agent that can fix the
issues," and "the audit agent gets the context of the implementation."

## D4 — CTO remediations embed into the next task doc

**Context.** Operator wants CTO-review problems/fixes read and embedded into the next task's implementation.

**Decision.** This flow already exists and is retained/strengthened: `cto-review.sh` writes
`CTO_<N>_review.md` + `CTO_<N>_remediation_map.json`; `generate-remediation-tasks.sh` appends each future-task
remediation as an acceptance criterion to the named upcoming task doc; CTO deferred items also land in the gaps
ledger. So when a stage is implemented, the prior CTO's relevant fixes are part of its acceptance criteria.

## D5 — `system-designer` role + KB_24 (HLD/LLD)

**Decision.** New read/design role `system-designer` (`.claude/skills/system-designer/SKILL.md`) owns
`KB_24_System_Design_HLD_LLD.md` (initial HLD + LLD authored). Added to CLAUDE.md §3 + SKILLS.md. Shift to this
role for design work before implementation; hand off to engineer roles to build.

## Risk register references
- Strengthens "theatre-shipped stage" + "over-scope" mitigations (independent audit + gaps ledger + design altitude).
- No new high-risk surface.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: ldL5xcoIAPbY4yIotyZHg1oa7YZWqT2y8xyOcImo5/9l5Jdv3jbpxMQRn1wA/Itsm9a3l6H2xc5kg7ZDZ/9QOPj4XL25AW/xfaB8cqUf6UYxNQi1DXBbB6kJMwowOdE7mIHvh+vrV5yGDc3R4ZRSr+JkXKGCgE3js5WIWGMHnrFGH5ZMaq1cQo4FGwPOmMhGkseCgRacDYq21XFR+u2GuFDfRd+gHpIUBJFqcFeyRkkKLlvBz82Ra4zgjT2dUwsEnjUbJkLl4pTYwHDe9NAxCSjIqZ5jzkVGtFd99K28txBfgEOb8d+iFHDY2rygN5iJ+5oXMpZR5nNLtFKqRN/f/8yVDH8rbaUn4rJBQPmpyo069n+iGM/cwip2cErkwuq0muDUD0rGNB4BaW8a3wI9ffwSBDlVEzHC+x6pNStBPaaIO4gTWY5ufVb1dxT4f+81xthVgsmSgyKe+iuNJ7aoAmid9GnTKK77cdxAqWyhPqj1sDf6pJ5FwHVaRqP9RJymYaZEqMhV7Fik/EnssNqIQyaj8A0zn0zihlLwQ5MYN94hk4ctQ0GS/LIEzWU7CrwaRyq+1vJvCzWILqHIR8rAcg+PKJ9ktaa+zKJTlWTDRHRrSQJxLDEhPipibfnp8yyKJn/tlHmHtBrHmB/u+GMBKiwgF6BmSHgb1FnAXtfX3IFO8Qkh+5aCPSAFhAzMnORaSVI4+9GErcyrRseGr+MhOdXCM34i0pVgxB3xE8tY1oyRJ5DnNwIChNv8WM8hmthJ+YolFIspjWk60aymL/5CibQTAc3fEBUQBb+Q3WT/YcfJZNInNuF3uhvdBRs9pyNlS7PdQItVFMik7YrWgl1olLooNiRIk33jlOyyvsOmdOac3QF3IPfFX/xN9YrfIO28rjI1AuSY4oOxTWhQwZPYW3gnPIheNNBAiUkjHdulSpkz5T+Jyq4sgh2pRp7QliY/UMR+NAS2vDrgjQms41qUFeffo7S52wgSMQzXhgdd+WEWmVdm2JBiUfW+Fd009dLbSnEpHyNs0WaSyG+yTa/u69RwYwYe985aji1r6ApxQRckOgF3q0wArBWVZZ/IcAWRooayK/DphJyVoia3fTq4x+VNNGRfdWwKR/LrWEpMY5QNonAEkBCt3bQxS4NPDE8x4fhTcwO8KDva0Cjk6XPPw974na0gb1G/gIR0lyx4K81HasAb/a2l+WhjMsihPnjTpKl/fxPYtXa1uK4Nfgsc3HIE/S2SKibPdFf8ALfycSZWhvAaMLhDY9PlmOXZA2VppQS8Sxt6ifSLB3MqZ1+7mbn0AP4dXH8I1KPEBclODs72nrlSD2OvpSi1ITlsqm5l4TTkgSC0pMpKLhanHIvvhCmki4PR5ZrFpCsGtk4ifmC+NN6YWa2ERieGZFhZxi//rPrwCp2rHTWxMrV9rDatnQuO2/1c1rYnc0qBHCyalOXoW3TbXcqCxArt9XrJ9T6n0kVdQofEMLRh6YH+7C5REYkNlavJiee4aBAYGcmSgDT/bRoaTFyaVYewm0o0BsNvJGe+qZop3llyGXNvu87X3JePd1R1zbK2+3GJTEBqF2eOhx6TYNEq7lFZXE1kY4Nuv9o68Q51ecgX8iy/1TvvuD1vfrxt4sQbKFKFkPY59FCKpNZqRdPaqiCpfHL8pvV/8e4QYeTSFekZtB+U6CSwx1Vb3TPlXlYy2g3CFEPU1vmjpQ7G24lfnoCnfU4/Twc+m02SLKyq4GY5Y3M0GbvbiAV/nsa6cTKaJobVCeyXVWhzL1hVKiEMe3sde8WVTPRgRWdf9ylCpLR/F+A1mS5JDmzpCEk8xNPYrDG5mGpNqs/gopYE9pyGFNXp263RE+0f7SJXsDIS/UW3ZO9ZN758hSswN2QxoA7EsbnX8rure7LRLw7/ueiDoBjfAfxKMRfeSDB5S5hTQbVdLdRyMT0LCFsRhop9Lvkz+6B+obAAX+v1AMu7xy+lV6jG9JH7tWuLi4w8UDsiGkAYmDuO9TJHh8oaLh2zuNaO2HqosZM2s+mIjv002P2G2GcoqHDhHDfvIqJm/IAXe1bJWIuVZ6IF8415k7klGC04qN6EHOZ1FB2qEcXRg3hgJCRZeGnu2/CDEtR9icKFkADemy5NVwlw8kSpo5WuEErhivxak03LydNeSXvY6gsjEat5q0nGoHkZy2ksWMWcpKwP+aM5FyicDENX3QFY59Hk1HEGVFPbwcwvg2DAyCMv2lWt40m+IcubPJKiqb9Wfu0JTc/fBoBxOf0nq5hRoOyJVFNq0gT7ozyUgjPrMiULc7NgOlNUOZwsOocmDq18p/B33oicZ/nFmw0Jg+WsE8d1D5pc9fzznhVw4cu9xwJZXJuv6gk4eOSee6xCGyBc6uq7Qb1OZsilu/unONv3wWqLqRvXjM94opmNQZ952wVREOYGDuwBVabbaSdqMY/mcyf/jg6xCfIcQmrp3CtVlLbkGmObdP1F4/IjDM9+Z/AvEUe4a1xoHbgNGahff3AEaa+8br8aodov4HPmw3hJeGnvAT8+OVC+rFr+xtSJf5RFeyRGueiAcscJjjYDMGwVAi5fW5P34X8p3igTQTja4G0rDHv2RfsdZfFQNjdaTt1jjiNM1OM6pzqcs8/Yvbg6J7v4t2PrCE5WPGWpTVOv498hWX8wA7PoM594s7cgU09asHk+SMRZLEj/9w7Q/D3ZctKC+Cmdp6zA0DaRYl/HcTKJBUQ/zDtHoLACMj+HYo9kcMKhcFIkK6mPD73tIceGY7574LSUpqx41Fa1520u8QDRMRcclnSaCmZLbnfQQPNQlhK0t7gm75pE/cqA9ABpxnzh7FqFnjT4X3YemsFLZATmfXiLkYolmoyZ8dqqAq4tHBnkl6vxhWC0o02hRp3Fk+PxzsD6bq3b1Be5pIRQpToDb2T9STR6GwubRzMnPxBBB3pZnDm8ydW9ShNgubY+l5fyWU9WNKMFlnL0IpFKG09FcRgFCNH032lh73fz+Zppa3YdwOueUPlOFzhz8Vpuu02NgHGzJlCMSV6ZyEbUCn2vu6nmooaO+ulMGw/U4WOITmgRw0ektsiAzweYyIsQX+lUJdBaTJAL3SZyV0y7IYH6uLrecQ+pHNf0ZTr6SjcZKBo7GAczo/K8czxhGn0lmVrxk0R40KOtMxNsC8E/7OD5PWaKjxX/nSHjPcgnagh6++whcCWMz0NHY2a88j0dD34DOsgTi0OA9aNotpwmWwW1Ze480VrIS2iPOV7mcrejJOGo5a/1IJCmysZcXqoSU2+J4dq5e+jrhxL0iI5Q/Oa/IW2V3DKdMnDqHqujSfO7oeeqU0PmXklJgAidlbmkUfzRnDiyNsHKO9kvtN58SVkO+nTLoZLZFffOFxsS9A2neQy1UO22BI4KNJJ2znW/gvGv9eRriQE/Yym3b1OfnUlthwFtv5eov1ZrjrVNGEkuyLY+jy4bYOJzsHo9uth30KAYa6f/4kMRCGXeyMC6Xplyeivo8yeqqYXBpbIlY0S4tnTe3MFGBkug5jMKp0i4MvPy/kASsG9DS5RFh/ZzZtFLbmDBwBDLs6RkDUHXZzhjPHMHGRl6J7y3YwhjC8r5qcKiLRg5wRuh0lUrxMG9k01QYyb8djt/S2rv5jQ2JBYcUmguEJZ5CWXT5B4c+zbuLpP38JGE+Z11SgaBDFTx1yxCDP8FSabIVobe3ZMvbNZW2Y+3kitBeyjZk6WYs4womFPKgulCCwZm+OJs/dg1CHeCjoNbFo6U/UUWgQU9INof5axc4Fg9Qqnv4XAKpY9wvdIEfwIkNS3Jzv9YPfn09HJMpmx3uf/mfCaNf0KMly+ooB4aj43GkViokxj9FvFMAnG83UdwhYbDdqNaVDzMTz0NNLmb33zSSFi8kzpoeX4CtikDpH0ARTRf0QAtO+/OIQmCFwl+ggPS6kzNQgvJQsJCrc4R85ZQvhu8c8gtg6naqMtCVDDw8kSnlCsCmQCwV1ghV+4OdUEgyP8d6TVVPlMcxTuMJpnaF606DqQBqTTSp9NSUCu6kvYSO7ZIj6ndFiZOT3njvuvOI9QySMcpB4g3ttZDMXZh19t9Cpgjds48JE6SqHL5NrahaMDucnefeVvcqbkzmbX+eHHadZFA1sUEW3pmEgVouG8FTeCrDF6xPgibf1zhWQTaGrYb530CUTXE0+s8g+C1ozicZZJg2QUyL9aY6K5NCvI0Wf/Gmw35Y246HTCk4J3VoH2nK8d0bdOfAhe7d5ZEC5h+hS+6EkkDdteO2mBBvc0Pa4yGuQLUnxUOGvNMEUiHtC6xIEdLijYd31uTK1YDzf5Phw0A4t1dlHlfuTJqo40ZM2OiwdDa3egGEVKS45T7Q2JtmqiwNWqUt8xKhpfE2/r8AAAAAAAAAAAAAAAAAAAAAAAAAAAACQ4QFhsi -->
