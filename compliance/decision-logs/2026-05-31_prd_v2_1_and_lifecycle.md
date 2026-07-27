# ADR — PRD v2.1, EU AI Act timeline correction, spec hardening & task-lifecycle reordering (2026-05-31)

**Status**: accepted
**Stage**: cross-cutting (verification/update pass; not a numbered stage)
**Author**: agentic-governance-engineer persona (Claude session, 2026-05-31); operator-directed
**Related task doc**: n/a (governance pass) — paired with Stage 3 work in `tasks/STAGE_03_ws_broker.md`
**KB updates**: KB_08, KB_12, KB_13, KB_15, KB_18, KB_19, KB_23 (new), KB_README; CLAUDE.md §5; TASKS_README

This ADR records the decisions made during an operator-requested verification/research pass: hardening the
product spec, correcting a time-sensitive regulatory fact, and fixing the task-document lifecycle ordering.
Full sourced rationale: `research/initial-research.md` §11 and `research/market-analysis/index.html`.

---

## D1 — PRD v2.1 as a NEW file (v2 preserved)

**Context.** The spec needed: explicit product specifications/objectives, target evals + quantitative
benchmarks, an ecosystem/integration narrative, an operator-dashboard requirement, a pluggable QSC→HSM
crypto-provider requirement, a production-grade workflow requirement, and EU AI Act timeline corrections.
CLAUDE.md rule 6 discourages editing existing PRD versions.

**Decision.** Create `PRD-ai-embodied-agent-v2.1.md` as an additive increment; leave PRD v2.0 untouched.
v2.1 self-describes the relationship (v2.0 remains the authoritative architecture base; v2.1 wins on dates
and metrics where they conflict). Cross-references live in editable places (KB_README, this ADR), not in v2.

**Why.** Operator chose the conservative "new file" option; it respects rule 6's append-only spirit and keeps
v2.0 as a clean baseline for diffing.

**Consequences.** Two PRD files to read; v2.1 §v2.1.10 lists the related docs to avoid drift.

## D2 — EU AI Act high-risk timeline corrected to 2 Dec 2027

**Context.** v2.0 (and KB_12/KB_18) stated "enforcement 2026-08-02 for high-risk." On 2026-05-07 the Council +
Parliament agreed a "Digital Omnibus on AI" deferring high-risk Annex III to **2 Dec 2027**, Annex I to 2 Aug
2028, sandboxes to 2 Aug 2027 (post knowledge-cutoff; web-verified — Council press release, Gibson Dunn,
Covington).

**Decision.** Correct the dates in KB_12/KB_18 (strikethrough-not-delete per KB rule) and PRD v2.1 §v2.1.8;
reposition the go-to-market to lead with PQC + functional safety + vendor-neutrality near-term, with
EU-AI-Act readiness as the 2027 reference-architecture play.

**Why.** Honesty rule: never present outdated regulatory facts as current. The slip materially changes the
near-term sales motion.

**Consequences.** Compliance remains core (manufacturing stays Annex III high-risk); only the clock moved.
Risk register row 2 (EU AI Act softening) is now partially realised — track.

## D3 — Pluggable QSC→HSM provider boundary locked as spec (not implemented early)

**Context.** Operator requirement: a purchased HSM must replace built-in software key generation with no
disruption. `backend/crypto/` does not exist (Stage 13.5) and liboqs is Docker-only on Windows. Market check
confirmed every serious HSM (Entrust, Thales, Utimaco) exposes PQC via PKCS#11.

**Decision.** Lock a `KeyProvider` ABC + factory + config-driven backend selection
(software-liboqs / PKCS#11 / Vault) + a crypto-agility "HSM swap with no code change" acceptance test in
PRD v2.1 §v2.1.5 and KB_13. Implement at Stage 13.5 per sequencing — do **not** scaffold 11 stages early.

**Why.** PKCS#11 is the correct vendor-neutral abstraction (validated by the market). Jumping ahead would
violate stage sequencing and the audit-baseline discipline.

**Consequences.** The "buy-an-HSM" swap is exercised in dev via SoftHSM on the same PKCS#11 driver before any
customer purchase. Audit-chain rows already carry `key_version`+`algorithm` to survive the swap.

## D4 — Operator dashboard + evals/benchmarks specified

**Context.** Operator wanted an operator dashboard tracking agentic vs non-agentic activity with alarming +
reporting, plus clear target evals and benchmarks.

**Decision.** Add the operator-dashboard requirement (PRD v2.1 §v2.1.4; telemetry/alarm contract in KB_15;
page spec in KB_08) with an `actor_class ∈ {agent,human,system,external}` tag on every activity event; add a
new `KB_23_Evals_and_Benchmarks.md` and PRD v2.1 §v2.1.2 consolidating SLOs/eval suites/datasets/CI gates.

**Why.** Distinguishing agentic vs non-agentic activity is an EU AI Act Art. 14 human-oversight enabler;
measurable eval contracts prevent theatrical metrics.

**Consequences.** Dashboard implementation is phased Stages 3→19 (rides on the Stage 3 WS broker).

## D5 — Task-lifecycle reordering: seed next task doc BEFORE KB/.md updates

**Context.** Operator was confused about when the next task document is created. Previously the only
generation point was the last line of `close-task.sh` (after KB_TASK_LOG validation, baseline rewrite, status
flip), so the next doc did not exist while the operator authored the KB entries.

**Decision.** Add `scripts/seed-next-task.sh <stage>` — a guarded, idempotent wrapper over
`next-task.sh --from <stage>` run at the END of the previous task, BEFORE KB/.md updates. `close-task.sh`'s
`next-task.sh` call becomes an explicit idempotent safety net (no-op if the doc exists; `next-task.sh` already
never clobbers). Update CLAUDE.md §5, KB_README, and TASKS_README diagrams to the new order.

**Why.** Removes the ambiguity the operator hit; makes the "next task doc is born here" moment explicit and
deterministic. No behaviour is bypassed — the closure ritual is unchanged except for the safety-net comment.

**Consequences.** New order: implement → audit → rectify → author hand-off → **seed-next-task** → KB/.md
updates → close. Dry-run verified (`seed-next-task.sh 2` correctly no-ops on the existing Stage 3 doc).

## D6 — `.audit-baseline` doc/memory references corrected to 436

**Context.** The live `.audit-baseline` reads 436 (post Stage 2), but CLAUDE.md said 439 and a memory said 441.

**Decision.** Correct CLAUDE.md rule 1 and the audit-conventions memory to 436. The `.audit-baseline` file
itself is NOT hand-edited (owned by `close-task.sh`).

**Why.** Stale baseline numbers mislead the audit discipline.

**Consequences.** Docs/memory now agree with the live file.

## Risk register references
- Row 2 (EU AI Act softening) — partially realised (D2); mitigation already on file (don't be compliance-only).
- A new row may be warranted: "compliance-led sales motion weakened by 2027 deferral" — propose at next risk review.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: Tbf/aUalYNgDDhvuxEoI0a6C/EQjnJ+c3pMAu9GI9/dXx1RvoUjah2GbBmxIjN5nCckpNCoKA94lKh2oWCK8gi+15OyI52UqnkYTeuNsP8c/GEm2Aysfrg32+17QniKJIbAD2ZNSBT1ECDKC951JTkArRYtuDy1LRuhTUDtrEdZ8ieVzLBxBN1hZxf4MsbOcV0I2zSUcR6THwTrU407/9+3sXEnXX7/STT1KfzGkZbVtiRItSkcAtxQxf1hSeADHoULRu4Pt4Bk0EJiSdVOcXYvhln9vMaVJXZ3nuGr17GP+31j2crawlRQYwl9TDVH23JeEGBxr98c7+DKXHScDnsVu5WyRDtzEXWVbi2M+yGP7Rv1K/yDRfepmg3n1ijKovx77F82xcW+3rj/uJUv1gbI9RBtQjyNSOOV9MU6T65liqdUpssgE7po1SuDcyuRdPpWNNHw2LwhEWw+AmTNUZe68GhIlccbrYignQGl0t4kbOl6bWg+ahnCx7Wih84WgDmcMYcGosR89fxmoZ+BeUhZKLskfG+keWqOTNPNx/tO/OfMAar+BUFPc3ze/ts5OSBgTB9cSoo9xR7KzMouGF6qOn24qoMFKIEAbopP+4bKT18j2IBqFinYXB/wVf8cCH1sJ281N2+VNbMhuKV8mhUlyhzDtIF8tKIH4MsxyhXFLgdxPj3kChraWp4PXT/99tUQvCUfbAkQhHp2oZIEl8KmAe3hki3tRxzaRdsO6l86S1kYRyuVXzdXZIQ4p7gNz7ZVnOVEAsRmZtMWOPBjwwAEdNWauF5q9TqK3RIqJmm5MGY+nNn9NOZ7ibf/Zv9t2lb04Ar5ok+fOquElqSR8Vj5T9ZhJbRdsO34dAVrv+nuvYWyqsZR0wFyf4bwlgsP2WpJxwInyaMXj9Vvm1v3ekgL6n8wfyviV52Fprv6ND10TTli+mdFNftChp+LsyvclOFnDW+9zlm8SPJ0kLf3oaLfDjVgxa3baOe1nelRa+4jsi6ldEKIiOQgCSrs5/wVZJCzijsstIpDwLwPgtWvGr0mEf5bzBmCeV5dW1+inSQM1/zhbV0/gvbZKRGvKWTluypK9atz/8pqOEJ3cCGtx8Zrq+XuRRhkLAefS4SUtRqqHjU1R7CeMgTOeW4YtgHxGOJrbIroF6BJdsTFeeduo5dyDJDGVKhOFwIZAn4+qzVE7SmycKQ6jyLHGX6vUA6485qJ7GKrbdPc2SPd1HA1Dcef0Q3VNvJ3EDvX1ZYdvWgodipwR+8uMdJ8t2GK+xGTRmzeqn2EWEkpnAUwSO0712wqY9oE7FsckB1hpIdrA6JmfQFaW52alyI8C8ERk9kNV75wIyQJQFLnPCQBvfnZIKJGdIVetmukYWX1nCSP1AT2rCi9M3Bdb/Y0CqeSxNhlRLtcyEEooxa9iqhk3FMY8OWBgEIkvNYDWo72W87DSPEHQWSJe5eRBg0RUh0c112owqMIp1DYUC0vdeuNE13Njqn3+TPHzxSka0QgUIoNhJOP5IPGNPyt3Qd9OhInm1m3iU7EolSoBotDjiTi8rk3S+Z7aCpWyHW9QjgwfzqOvt4zPfrrqsJA8Xpt7sgmWUWOEwAN8bL2oG/cjjmMBnlGOMsMAkS6ugLcKbTKD2a7hIGJPMfQlK6J4tTOl0StrWxkfpm1u1hKhqP2b7Wo4pHBH/GCAkA1c0lVKiHOAOcqPQrKxAg1SqvTOkegFsJLjS/wPW6RHezg3uG18ZXiNugMHZCEdXCaA0s6QdaERE3gbEQvrxOGm0KKMJstNQyOIF0/GvPf+vkwEi57hy39sxc7S8ovFdkv8ykF5kZHCuPtoub5nRABrLfJIAQUz4/cGsQFgyjPJEFkR2Int7zVaNGZO9xjpZeDNLE5wKZ+uJEnCerRcDdeUL95Dt4Er0b3e6+RPJri4ugxWhkmeh23CHRZzdHnexeO8jIlbgI6pNAmeAsJff7Aupcf78hJWdYgfRGclUMMdd1wTiekmQXUgjSwTykKDOV2wcdBFpymvSC+e4pPn0imIREYXZ2tta2OBMlRZFOPx5R1vKsljx2Ra4wUcxQRkTuMONOuzL2SIpOMdzSW4YdIejofXw9UEzr5hQwSymavWtf9IsVG2jtdypxdn8zQ/4giCO3Zs0VS7vgKetbwPMbp4HyMTIFU0Nh1Qz/FYNRbzQ4PU+jdd3lv5BmxtDpCV+WomB7CahSBigZhjYAC5G7WBeSC8O2Pa27fbvNIEWLCbR2AARuWYkv7LI6Ic/pfvRqz5yX5aZsvNGahiQz4VMwwpjhuY4SY2WRLjx7+DL2I/qgiKlWW9XgcKV/9N+CSuNKNiKF0U2QUDmPV33WqFbCuOgX7JcHZijXku20FDsXRhpZWcuBvA/az5EfG1gIEtZFI47+OVI50v9YprM3AB3k3cWB9lV99ZMFmdL3BGURCz8diX1G+7j4a4EdQr7pm5JECKUkxr14m7tvjCeN6Vwn4pUC7O1GmXaKgiTar2SxVHk8RVgEROIOeLYzpov5D4DWYWVdmsiF2aHKq7nvmr7y/nSdVIrOgimhvfJYGjZ5e61k+rmLnbnAY/hHajDNLZn6125j/ffeIvw4qKILS1BHbDDOnvBr7+g50mzdpzLgko04rzyLV7bb81y2xU20wY/8KJKhxJ+B8r0McMcGyhoE84ooBpw3XAz13o72aSokSuuNPv8tE4p1k6xQTUnnIaxbDIvJJdY6DHuHNE9q6Q/xLBvLeE7Yq/7XaFwWNZv78oNrdwDjGapI5u1afAHDWyBRdmXkRiaU3WaVn/0vOvlAr2rwVU/9Cdxnvpxob6lYaPhyAzgpG+AjOmufWsqcm8dORej2QU128vLqBzLt5xU1XoUJ9LlOTLEg0kE6U5KWIUCfLERXx7I8PE2qmcIITsYci4/6cwWda1fAiv0vLDyB3IppRPPO9+UUOyNefsxz5NIe8rVVkQyTLrIF9Q00YTW3IZCo6RrI3ISWanFggkuG3A1c/mfR7oLzfs+auluMbkRu0QoAFoh/EcwIXzpTdy408lgUfugtzaXlLB9hKAfPaukZDpfy8qc13M30PqmVi3Xdj5yPG2THrkRtXWZLxQ9dWp1OkfFNa3D6wPsHd3tw9+gUKPNmKjrqUSo4QHwuR0SrJZeSoicn6oLQR5q2zNvIfKcpZ37Muv6WZAE6GLVtMM3ZwYo7hju6bWmR86BzA+HS7j6MVxCChb8jigrpKefAuhvg3HDwFg4JqCC0oZhAWLGD0KKe2xtjTMNcEMRe6f4LWf1+UeXjASCRA7nSkd5vJmPpWGfIfyafDcjR3e9rMPLotqgIDuNbUhvPNfPk/AhKESw8WnAozsWtVf1Vss7YjKeRlCQCygbLhlneg7048kBzDEl6hE/cF7WQOsZF/LAf9yhwefTIEt9IjCUyFZTlExloDdYzaA/9X+T6aMq9aAIJcmlcqMYXWHQ9AGbolG7cG9hdwoLT1cuz8tzyE/J3mMZvu1+YcHoj4I/69hgUgsCEXftKw0bY/TiLcpn3x5U4nd2YGyk/MBe+dTzyDXUloHh1t8mLJBOwCrZvXPK/3jzHk7LLXoj2/LUfnMdqV0bvSTbLVunPlldceQjEr48kJR1A/M7udQmv6dd6lS8agoXxsIMBXJBTJ1MxzLhHV8/EtyXCflLCprmLMH//oiRVBUKnl3/CraMKxcLjWCgQVnkCWvivWAUpNm0lZc1ywffAglqcVAj4DWBO0FCZCq0RoHTosJ20XAbAx6Tn2gVOO3mj+YyghFySMxL2DgtOA352DTVH31hbFY8+IqqML56U6jBiw6HNLFQX7A2FSLNNVh4WVyYlNxJOwZZWOHgYl2AWcKfN0nJ3Srj/VY3b++93gdm5snuQk0hpgKAkwtnw7RLKhwmxJgop37fu9RHTG3w6PxAX4oO9j1ujiSsVOy9YT/A2baHyvWq2V5w4CcIxlrvi0W5+BaZzZ1TWGoz/UJmo0vEL6xexYQ4Ym8Gua+4eA+qA/S3zCs3JRr9dPk11H7zZxG2b4c3baNHLX7TwN/B2VIfHBwMr3ixaTQY8B8ko6cZClGEDtf/x2KbKQJ9CmowGQgFBy8w7OUFDsYOx49CAL7y0RWi2oI6YCL5Tvy8SFRTi09tmEBKod3TKWdcqIoELI7gEEEoHG/+VVq/dOpILtGtHaRbgyhYohOARpnqf9zE5gr2Zd+Iaf6X5PoM++eK3Qx9yD/pTfpPp3saBR6db/BXRgV7OpwjQmc8plFMtXEdCothqSiehd7qvU/PgWCzS0YZS4Oo3GsB9HZaDQFnM9+EDXNy7YABP8H6Fxj0EBaeMs9op+Nqs+Xvn4tZYSZ4vf9FR02hLnSPkluwMQDGBtkktHr9mqYp7/A5T9bXYHa3+UAAAAAAAAAAAAAAAAAAAAABw0SGiAn -->
