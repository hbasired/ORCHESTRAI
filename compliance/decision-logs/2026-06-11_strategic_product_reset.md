# ADR — Strategic Product Reset: PRD v3 Consolidation, product-manager Role, Stage 6 = Vertical Slice v0

**Date**: 2026-06-11
**Status**: Accepted
**Author personas**: `product-manager` (new, created by this reset) + `agentic-governance-engineer`
**Type**: Out-of-band strategic reset (NOT a numbered stage; precedent: `2026-05-18_prd_v2_repositioning.md`)
**Research trail**: `research/initial-research.md §14` (all market figures sourced there)
**Companion artifacts**: `research/market-viability-2026-06/index.html` · `research/strategic-reset-explainer/index.html` · `PRD-ai-embodied-agent-v3.md` · `knowledge-base/KB_26_Product_Market_Strategy.md`

---

## Context

1. **Operator mandate (2026-06-11).** An irregular check: absorb full system context, find and fix loopholes, run fresh market research (viability, competition, startup-worthiness, integration into real companies), create a new PRD, add a product-manager skill, define Stage 6 and what follows, and produce sourced HTML artifacts — honest, no mocking, niche-and-differentiator focused, secure, production-grade.
2. **CTO Checkpoint #1 verdict (interim, 2026-05-31; independent pass owed = G-031):** "spec-deep, code-thin; freeze new spec expansion; build ONE end-to-end vertical slice (predict→diagnose→intervene on the machine-failure scenario) before widening." This reset therefore CONSOLIDATES and VALIDATES; it adds zero build scope.
3. **PRD sprawl.** The active spec was a four-file chain (v2.0 → v2.1 → v2.2 → v2.3) a reader had to merge mentally, with internal date/positioning corrections layered across files.
4. **Confirmed loopholes** (all process/doc level; operator chose process-only fixes, code gaps stay staged):
   - `pre_tool_use.sh` rule 4 protected only PRD **v1** — v2.0–v2.3 were editable, violating hard rule 6.
   - `CLAUDE.md` stale: §4 rule 1 said baseline "436, post Stage 2" (actual 402, post Stage 5); §11 said Stage 2 was next (actual: Stage 6); §1/§8 pointed at v2.0 ignoring v2.1–v2.3.
   - Role mapping duplicated across `scripts/start-task.sh` and `.claude/hooks/lib/context_loader.py` (drift risk); no product-manager role existed anywhere.
   - `SKILLS.md` ("Eleven personas") and `KB_README.md` ("18 body files", "15-stage plan") stale.
   - Append-only on KB_TASK_LOG/research log is convention-only (no hook). Stray junk dir `backend;C\` at repo root.
5. **Market deltas (June 2026, research §14):** InOrbit open-sourced OpenRobOps (orchestration commoditized); Cisco completed the Galileo acquisition 2026-05-22 (agent-reliability category validated + vacated); Siemens+NVIDIA "Industrial AI OS" + Erlangen fully-AI factory blueprint (incumbent bundling intensified); EU AI Act Digital Omnibus provisional agreement fixes Annex III at 2 Dec 2027 (formal adoption expected before 2 Aug 2026); CNSA 2.0 NSS parameter sets are ML-KEM-1024/ML-DSA-87 (ours are level-3 — claim language corrected); humanoid orchestration is OEM-bundled (neutrality more valuable); integration overhead = 50–100% of hardware cost (the concrete pain our adapters attack).

## Decisions

**D1 — PRD v3 consolidates and freezes the chain.** `PRD-ai-embodied-agent-v3.md` (new file) is the single authoritative spec: v2.0 architecture + v2.1 SLOs/dashboard/KeyProvider + v2.2 three-leg USP + v2.3 self-healing headline, PLUS new market-grounded sections (problems-to-solve matrix §2, ICP/personas §14, GTM/integration playbook §15, monetization options §16, business metrics §17-E, de-risked roadmap §18, honest viability §19). All earlier PRD versions become archival-frozen. v3 adds **no new build stages**.

**D2 — PRD-protection hook generalized.** `pre_tool_use.sh` rule 4 now blocks edits to ANY existing `PRD-ai-embodied-agent*.md` (basename match + file-exists); creating the next version file stays allowed. Deliberately **no env-var escape** (stricter than the `.audit-baseline` precedent): a PRD correction is always a new version file. Ledgered as G-037 (RESOLVED).

**D3 — `product-manager` role created and wired (4 points).** `.claude/skills/product-manager/SKILL.md` (7-section persona; owns PRD chain stewardship, KB_26, research artifacts; forbidden from code and from scope expansion without ADR + CTO alignment); slug keywords added to `scripts/start-task.sh` (`market, gtm, pricing, positioning, persona, icp, viability, pitch, prd`) and to `context_loader.py` KEYWORD_TABLE; rows added to `SKILLS.md` (now Twelve) and CLAUDE.md §3; hand-off line added to `agentic-governance-engineer`. Known fragility of substring matching ledgered as G-038.

**D4 — Stage 6 = Vertical Slice v0** (`tasks/STAGE_06_vertical_slice_predict_diagnose.md`, replacing the TBD seed; git-renamed to preserve history). Scope: live SimPy telemetry → failure predictor (AC1); deterministic root-cause diagnosis v0, no LLM (AC2); sim-only intervention via the coordinator (AC3); **measured A/B intervention-vs-none** (AC4); events on the existing envelope (AC5); baseline < 402 (AC6); independent audit PASS (AC7); KB updates (AC8). The CTO remediation map's "vertical slice → Stage 11" is REINTERPRETED (not edited): **v0 at Stage 6, production slice at Stage 11** — G-005/G-014/G-025/G-026 remain targeted at 11. Pre-requisites include the owed G-031 (independent CTO pass) and G-001 (Stage 3 independent re-audit) at stage open, per operator decision.

**D5 — Roadmap re-sequenced to actuals; no new stages.** PRD v3 §18 records what actually shipped (4 = PdM, 5 = demand; defect detection moved to 9), inserts the slice at 6, and defers 6.5 energy + N-domain + dynamic features until after the production slice — depth before breadth, per CTO #1.

**D6 — KB_26 created; KB_11 refreshed.** `KB_26_Product_Market_Strategy.md` (new; owner: product-manager; reviewed every CTO checkpoint; wins over KB_11 on positioning/claims conflicts). KB_11: strikethrough correction of the "EU AI Act Art. 14 compliant out of the box" overclaim; June-2026 comparables table appended (Galileo→Cisco, InOrbit/OpenRobOps, Ati/GRID, physical-AI funds); cross-pointers added. KB_README: KB_26 row + staleness fixes.

**D7 — Market verdict (summary; full sourced analysis in the HTML).** The lane is real and widened: the defensible position is **trust (signed evidence + functional safety + crypto-agility) × causal self-healing** running ABOVE commodity orchestration (integrate OpenRobOps/Open-RMF — new gap G-041). Startup-worthy **conditionally**: comparables and capital exist, but fundability requires the Stage 6 closed loop and a Stage 22 reference pilot (G-043). Honest non-wins recorded (distribution vs incumbents; sensor PdM; pure orchestration). PQC claim language corrected to "FIPS-aligned, CNSA-2.0-aware crypto-agility."

**D8 — CLAUDE.md anti-staleness pattern.** §11 retitled "Current Stage Pointer" with an explicit rule: it is a snapshot; `/begin` output wins on conflict; update at every stage close. §4 rule 1 now names `.audit-baseline` as the source of truth with the prose as snapshot. §5 documents the out-of-band reset lifecycle pattern (this ADR + 2026-05-18 as precedents).

## Why

- The operator's mandate (niche, differentiated, secure, profitable, startup-ready) and CTO #1's freeze-spec verdict are reconcilable only as consolidation + validation + a slice-first Stage 6 — which is what this reset does.
- A four-file PRD chain with a hook protecting only the oldest file was a real governance hole: the "frozen spec" rule was unenforced exactly where it mattered.
- Market evidence (not vibes) drove the niche sharpening: orchestration commoditization and the Galileo exit are observable events that re-anchor the moat on the trust stack + self-healing engine.

## Consequences

- **Audit baseline unchanged at 402** — governance/docs/scripts only; no `backend/` or `frontend-nextjs/` code edited; no stage closed, so no baseline ritual ran (out-of-band pattern, CLAUDE.md §5).
- All PRD files including v3 are now hook-frozen; the next PRD increment must be `PRD-ai-embodied-agent-v4.md`.
- **G-031 and G-001 remain OPEN** — now enforced as Stage 6 pre-requisites rather than free-floating debt.
- New ledger rows G-037..G-043 (one resolved: G-037). Code-level gaps (G-032 frontend type drift, G-036 demand wiring) deliberately NOT fixed out-of-band — operator decision; they stay at their target stages.
- KB_TASK_LOG receives an out-of-band entry (Stage-0-refresh shape) recording this reset.

## Alternatives rejected

1. **Stage 6 = next original-roadmap ML stage (defect detection / energy), slice at 11.** Rejected: repeats the breadth-outruns-build failure CTO #1 named; a third predictor before any diagnose/intervene exists adds spec, not proof.
2. **PRD v3 as another increment file (v2.4).** Rejected: the chain was the problem; CLAUDE.md hard rule 6 already anticipated v3 as the consolidation point.
3. **Version-aware hook exempting the newest PRD.** Rejected for strictness and simplicity: "newest" is ambiguous to a grep-level hook; all-frozen + new-file-always is unambiguous and matches the ADR pattern.
4. **Fixing G-032/G-036 code gaps in this reset.** Rejected by operator decision: code fixes outside a numbered stage bend the audit lifecycle; both stay ledgered at their target stages.
5. **Running the independent CTO pass inside this reset.** Rejected by operator decision (session-budget risk); folded into Stage 6 pre-requisites instead.

## References

- Research: `research/initial-research.md §14` (2026-06-11; all sources with URLs) · `research/market-viability-2026-06/index.html` (26 numbered sources)
- Prior ADRs: `2026-05-18_prd_v2_repositioning.md` · `2026-05-31_prd_v2_1_and_lifecycle.md` · `2026-05-31_usp_repositioning_and_process.md` · `2026-05-31_causal_self_healing_engine.md`
- CTO: `audits/CTO_1_review.md` (interim) · `audits/CTO_1_remediation_map.json` (reinterpreted per D4, not edited)
- Files changed by this reset: enumerated in `research/strategic-reset-explainer/index.html` §2 and the 2026-06-11 KB_TASK_LOG entry.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:28+00:00 -->
<!-- signature: 7v0Z6x8CE8LqxDP+DZyon+5f6YBqyI7rGdpVkf/kWF1IQWglJRtbPHKIh0vz5UKLHCLM5kItMeoWH3EUjZNCnZLRJhP8UG8GZwOCBuXDFuZtfgnNVAjRuSVV4denWB3EWd/JUi+n9uthHjx7gZprmNXl/ZxgC4QsZWzYgmNT1cOG6xgoSz+jsP65mIJYFVzBwMJvnoZenl6sj/KTppTtxEMXq318MuoR8gOCyqsmP2U5OMTrnBNFgsEFoPu1sYs7UGoIQbzNzTKoKlZxFJPKpAzMxuX+fqmA0NKGg+mY787EeeXoFCpZ1TNyqlQwWuaBjuGDsPtQV/QrT8h79NqikNUaWoaHjZ4h0/lgiUc4W37KYu6MUC93rXHH8xgO9JzMWyUh1/sLCrdwhRViemu7pTU4nYrc2AxGgGmYnO24WTOdWPUXkDoVLR7HwIUSF0Dp1f3Q+QZLxz5nOwei41+QGHyAIgK6Gf5mXB2UaNZicSmJM1RTVe+O7Q/l1AB/o0PXJsqfZzii+4RRXtcuSES6TdnOYAdsMq3dlzZLwXifaO6mAHrK5sT7L7ACCk4FJ6otBKLNNzIoMWRkxaEJg+ec3/gg/A2EZUuATmCjSvHV0kP5VP0zrX9/v6VUXeWZcVsiY1GD80vRFcry17YJiuwQUYgow28gBN2MKpGAhQhsls/koE6QBfaBqEOy2q4nMwAHdwgEaQUUhHM296ICFW4U1dFZNLF83XLoc8rW0tbxpOj9ulvP7BXbBmoycWgSHCO3lk0XB914JQKOglcTiVypIifdQHNIXU/4UIQMTL4vqNfX8qu0yVJxdoOXewlhDbedwBCOhfz48KgHTXMR9efJboswSvuy4BQgVRqED2xQpMMlD0mUZK7Rg9JZ/MpKQGW7DrbeyC4HHhlzpx69ryFhre4DMDf3SSVtQQuCU6mYboW5dBibEZ3wVMUTSJlq7gtDHsGELFbzC+qCl9ZHTuMYPBJcfgpqaesEKlmKMKII/1iga1jpLEMqjb1IKPQG3gIWZD7b2zDBrbFB1ljNjyInf6whHEft4jH7SI0JxgvCpQD3BsprtwRUtnJ9bscb8KXbrNKJeEOq4cDJxAmmChZtkii/S4/0oddQ02GR9fqCpDfXsMVDzTYFzL4lBue/zvNtdfVSvlrEfly/u6N+XPK0qcoN7++u3uyukOFs9KcDLnvoscACLaDcLL1mpXPYwvp5U0ZMYifhbR7eiQ+C4ySHeftOGHa/mbV3U0oRyxXeW8vGIrMdZINBb0kmO5CWfzubF4aX/7g/WcG0ZzwMquDs+VixyoNjB4pWRRp1fxSVmsO0wcWinNpm94Y1NbIDRhjde7LERtjaSu6WK77fpuec0Q4YjhH4b5AhFl9cEPMB/vcN1RKVstuWvq9qG0xwlYY/db5kJT/qKB2qJe0xsoj2U/pSiBukorW4l4OZUas0jUemL63QlK0s11frX4Ra/vcoiZ660ricgXmETc4tvWB2QFUI8oay+yBbv9g6JZSg86LOwCbgVA9At5MAsj7Ei3RxYv3HBQUjW83bpLypv0pCCd/2ilB85SlI97QZgCPS5FAEVT7nRO9jdPaSS3KvxQkbVv90t60WR0XdRMoWQ59lWd81SRsWdrI52XjfYsEICIpuDlA14sVhDDCGLhEIFMKUeBj7/7vDHgaXw0J66SlKG7KCrPXt7Hd+35TTvzV7U1kL0J8VI+eEx4rNhzafBGAdKdxHvEeqJdTfAt/rCpJGnh5xg0rI7y9P6DUk8Bj64y1J34nSUIXpAgb70duG87jpEW+vZxeGBOVSD3c6dwtNgHv8nAdY6KuW7Vs2TDntnNUzgf0Dkln0meail1OgqWW3vC7uXo/+Hect09FHiFc2GwTZJGAveRqL4dgk5xgHZ/7108GGaRjH1ZTh2BFB3qU6IsQQAAJtBmCQuYWoxv+KWbX6TCQpYA7a5e4OAWRjCG9564vGzIenra8KvyQ7Av2GhUDVCQw1w1DFWSoDafHcXAdvjQL6qupaBZY0pKNkZi+o94dSzJnLvho8p5cucjncdlOpCieePEpVt9fyVPFNe0nBs/A6xqeKKgnIcmNESKrDuIFsgKbcaNDMeITnbu2Q6o9dj+lD4ziy3ZXPIHXLo3hcf0Wo6WItX4khgCSdHzQzw0gzi6IkGx35FPWHA3QvBa1f8R2WBU24IxHZS+1f9qfN0Le/EWMjSd24Lv3HhaWe1HEmnpUqiYGN5pbfPfPp2LstoPGSMWj5coUMWhIY1pmPcJOyEIamZyg/jKpwAlGWiv8uCn2jQdRFjOQ/LydX+DwYlmWG6XDbBHI6MVEqf6y8utdMjXrdQbbpbKCA9HD4o5RZ9dlIjukYJo64bm5UyHghb0/0SAJ6XFIiFJUlhd+wuDvxBtaFh9w0Xl36/Xg4WqeYPwth19qea2p+QPlaYMLSKLzqTM9lTXsvwqSsomznbjWGZLrwji/mzpH6FkhJjcN3y0JEXl+78Q+5NhbleKB0/C8Oaf+TKHDcljMbf3v7jkXqdqvMQfUSNrNuNpEo47KTf8sG60Bg/n4sxJDluRxlSJYwx4YIJYfq3WWlYYZSUI8zlKhvXO3x6OqFk9PC6tVMebn8SvMrrzsA/5TbxyfxgvBJ1IYtonyQjAZt1YnVBODv7EBhZv174wMqQJnAHXfY4Rv9MA9qEJJ0pmyElKcZ5yjraZ+AEKs5tg6rOGkvhzOAdEJl0Uh9OzDY/c5Ydm7lQ8uIlLUpwL2LHiAkWbE9fbmWdr2oiAfND8TSMcwFFiWJPuTrSZlnxm5JmPggWaeY2Kr68dqfrjSOvHYk194KMsPFWBQvDqIDWLMAFJbEY1qspeN70RToiH+dRx63BF8mwUjkwRibfOhX5HIN8HGHzYTMMlC9CX+5Ng4QKkmc7RO3H9Iz8jS/Nf2K/s9TqkJC101CN6Rl2SDNFdAX+EuXbgJ7YQ6dKfRNtFeDEpS3XCWrwGY6QOTMHm84KQcL7pJ0fac1YA6DlnvojzXDzAfog1F9OSEwHKCc7FESiwwMT4aGlJb1ADo4zeR54djyHg8zWFY0O8ZnMTk8kYenaRSWx8YBzlx5JLbXrgfNTJQsImiRVbjr5N1PaCVIYcjkFMRQjrnxnUXZGkPE0E2JBW6CJkG70x4Vrp9lqWaIER4JM3l6+O4F2upVk+99T3XglF26o/X40owc60GWSmjI//OXS8zurfCdRBaHQOs9uaAuKT/J23iZgW8IoI5nGc0DxYgEMSr9RFMhaFZfIzrJCeM16B+QKibmNyOVaCDZ3xzTdnfjteQdK5H9wmrmMyGAm5+LCAbZ45Xskm6pL+AUOb6YNl5iE/2Y+oXQeyQ/PqOxXxfSmP5Kc8AWoEO1z7bthGScgALW1iLDKaArHnwSHCqfRprAjMpa6Ju72qFO5zu+ygsp1ub9OVHL9gvumOQuYTmSLoiGEY9q3ebVN5J3RzZ5OLOf6vNf7EyshbLRB/CCxeTdlDTiWwo/tdmoWPlA4NcuiAQ3bsWMrInpaVn3oDHRzSPNvuZo8cozFDtJPLFmdZPLxwb3Ru1wRH5BrOSn05NiYd2P6UYa7HMNWKwsdMdFIhCFDZBimQbZOfz8sHveAocvApKKpMAJfQgTaw1bUJRBAHxHUplN/Q1x3uiEnXzvbM+KbzPx9QAn/4coqXjK5XeGd0foN/MY7SuupShs5FCBbzV5EwLlsyfOJf4KNnE0UzEBDBBIcF78UmRDQ+ErKHMOyVPNptsSsPLVzs9XDTZmG6V5WuVX3MHUTsajqJWDmi4+B8LPbzx1+D724tCBFaGcIoZsyQZ+iBzk1MupbXYI5SMbvVqMAKUOUiPVglvmMxc8/kY0jMrphubAO0mtr71EsXtXpUYlLHphDEve9ixkprbQTMLEMSJ4Ttm/xNPJtghYlzp28OHCILxQc/sMfhabzCvv8RuGxkbjOVABBTcbiSgU5fPYUbCqGVJuWgCFDIiburGG94dLec4tfgyWqDp96aqtdrEl3ZO6fjNlkQkdTT91ODXrJL7eEWliLojooMHmP+fZk5AFQ7JPuuMl53WiTa1irDtRXYCV2YJd+7xSu2tT5mA2dTuO1fDsjrKPw8BGNHVnPbb9IHGGj9v1roRYU3keGpc3T6HNUOlF895x0mbHNfXkUDWyydB9JAyS0ielNxiGawPjxHeUqmbKENFA7jciVn8qwFljX98IqN/xi7s0H69EoLL0xcRB17w8rl1o0DVe7Nq6BMxfNXc+0C49RoFMS9fkAZHTChOiagUXt+heathVvbunJvXFStm5B09+YCQxS/r2PXV5MDIsWiI51/RCdx+rZ8ODel0GQVBsfbPP2Bk3QGygtfwjQ15mc8kjJV9qphUsNaoIEXLRAAAAAAAAAAAAAAAAAAAAAAAAAAAACA8VGh4i -->
