# ADR — Stage 32: Pilot-readiness package (charter + capability-readiness matrix + A/B protocol)

- **Date:** 2026-07-13
- **Status:** Accepted
- **Stage:** 32 (`tasks/STAGE_32_pilot_readiness_package.md`) — the FOURTH and final build stage of the
  operator-chosen post-Stage-28 arc (29 conversational → 30 live-wire → 31 detector hardening → **32 pilot-prep** →
  CTO #6). Docs-only; no backend/frontend code.
- **Roles:** `agentic-governance-engineer` / `compliance-engineer` (pilot governance + honest claim discipline) +
  `product-manager` (GTM/ICP posture, KB_26).
- **Research:** `research/initial-research.md §43` (pilot charter / predefined success criteria / A/B proof-of-value
  SOTA) — appended BEFORE writing (Hard Rule 11).

## Context

The build through Stage 31 is complete; the remaining conversion gap is the real pilot + published A/B (G-035/G-043) —
"the single biggest fundability/credibility gap." That real engagement is buyer-blocked (needs a customer + real
fleet, not free/local-buildable, Rule 9). What CAN be built now is the disciplined pilot package that lets a real
pilot start day-one — the thing ~60% of AI pilots skip (predefined success criteria) and fail without (research §43.1).

## Decisions & outcomes

1. **Pilot Charter template** (`compliance/pilot-charter-template.md`) — fixes scope/intended-purpose, per-capability
   success criteria + thresholds (each with its sim precursor), two HARD gates (0 unsafe actuations; audit chain
   verifies), a 4–6-week value window, roles/oversight (EU-AI-Act Art-26), and the **Scale / Iterate / Pivot / Stop**
   decision gates centred on business impact (research §43.1). This is the spine — a pilot can't start without agreed
   criteria.
2. **Capability-readiness matrix** (`compliance/capability-readiness-matrix.md`) — the honest sell: every capability
   tagged (sim-proven / benchmark-proven / built / real-data-blocked) with its REAL measured number cited to its
   stage + results file, its real-data dependency (G-035), and its pilot A/B hypothesis. A buyer sees exactly what is
   proven vs. what the pilot will test. No new or aspirational claims — every figure traces to a closed stage.
3. **A/B / proof-of-value protocol** (`compliance/pilot-ab-protocol.md`) — predefines the design (baseline window,
   assignment unit, primary + guardrail metrics, paired test + CI) and 5 per-capability hypotheses + the 2 hard gates,
   reusing the Stage-6/26/30 A/B harnesses (same statistics, on real data).
4. **Base kit extended** (`compliance/pilot-onboarding-kit.md §6`) — data-intake for the Stages-26–31 capabilities
   (demand forecaster real hourly demand, supply-chain data, GraphRAG SOP corpus, detector real-traffic), each with a
   re-fit path that keeps the model-card + red-team + safety-gate discipline.

## Honesty notes (Rule 1a — verified)

- **No real number is presented as a deployment result.** Every figure in the matrix/charter/protocol is labelled
  sim/benchmark and cited to its stage; the sim precursors are the A/B hypotheses' priors, NOT evidence of real-world
  effect. The two hard gates (0 unsafe actuations; chain verifies) are stated as production-ready PROPERTIES (they
  hold today), not pilot hypotheses.
- **The real pilot + published A/B + real-data re-fits stay honestly deferred** (G-035/G-043, buyer-blocked) — the
  ledger row is marked "buildable prep COMPLETE" but the gap stays OPEN.

## Consequences

- New: `compliance/{pilot-charter-template,capability-readiness-matrix,pilot-ab-protocol}.md` +
  `research/stage-explainers/STAGE_32/index.html`. Modified: `compliance/pilot-onboarding-kit.md` (§6), KB_26 (§13),
  `audits/OPEN_GAPS_LEDGER.md` (G-043 buildable-prep-complete note). **No backend/frontend code touched; new deps: none.**
- **Audit holds 3** (`--no-baseline-drop`: docs-only governance stage — no fakery patterns can be introduced by
  markdown). The four post-Stage-28 build stages (29–32) are complete.
- **What remains is buyer/accredited-body-blocked, not more building:** the real pilot + published A/B (G-035/G-043),
  accredited functional-safety certification + CE/registration (G-011), scale (G-066).

## References
- research §43 · `research/stage-explainers/STAGE_32/index.html` · `compliance/pilot-charter-template.md` ·
  `compliance/capability-readiness-matrix.md` · `compliance/pilot-ab-protocol.md` · `compliance/pilot-onboarding-kit.md` ·
  KB_26 §13 · G-035 / G-043 (`audits/OPEN_GAPS_LEDGER.md`) · ADR `2026-06-22_stage22_pilot_deployment_runbook.md` ·
  iternal.ai enterprise-AI-2026 · agility-at-scale pilot-and-PoC.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-13T06:36:07+00:00 -->
<!-- signature: BIbAr5CiaZlXkvv7dxG+rt9jKRJbVBigBShro5w0cqZqMwidIWXM2ZaHruJAwNloN2gYyxS0MBIfwG2PCIfewL8jqawxgUaNxgmfJp+FPIhjEI/0BBRdFM5gNEf76siW6pKrhGq5TZjRmvYz2zGnM4eUK2vy2aeedSoM/tKkad6xake0EixPs8/l4tZu1lnbtzh6B4wxfIsBIDxc6vurCYFlJODqufRkaw89EJxJQNahB7B6kObWb7WA3Ez6IASbOWcqe+8ekSS9pCCo7anrZXScniWKsXXc+VS6xWiaE39Ui+cRA9N1yNRi3yf5LDrtMqEgxduJxhhKueF0cX5kPQuT+f+egK5lTNYKcGdD/7kw9D5xIjgSdZnVTanEQw3Nr5wRvQD+lR4foHFA5S/zWsUjJobCUMlr9xJdq1SH2RV4tzM2aAzuzsqvIbzioj24cXZxbvCD9gpiRUBd3pfqxN13zIc5ZF2YFs2eL79jltn44vz3qmlqB1E22RFanw2L7I5xzpNv3BZLpBckaHooKKU+sqE0X9JNH4CWKfJnqGHyrnDZlie80Ej93yWIKLHwFlQow0XbaUhFs78ubZLO/X7E7Xs9OhhqTeL5IgSpIAkOnWLn6LATM4xTjgJR+UriKl1nfqjZ03aaekNf6qnpTeKyd6NHBQuZv319b4isqd1EvW9xZ1KGhO8QHrA0y9eVZx+x7FNrBISObCDpVEgPV2eXcZhQdRlESVdgmgAXjf9JU4Hq6Qgmmr1rvjRwEDcn7ZnNfnO7i0CRCDmkwrCxU4OgetEYqjG6BF/fcQ9nXRsvMg/OIC/U7Sd2eBhPHRvRh58YCE8iWlIKfr81ZYRNoJqchgcw9r6Btq7csxf8AOui8KG5NuGRMDVNzozj/I4yBESDdk1DXAc79W8bTsHMysdLx1kPpJGiIUC89fHI3v++arm2ifxbjFUu4V1ggmgKtBqLXkRkzOfCU+C6WsvjQTyF8fT8htVWrTC6A0TbdJ4y9jrcO8odvujZFdnl1s87KZ3hq+DuXSbCcaLOsWoaati1tF0BEC+egufbOYgvQf7gtGdXnHyrItSpt0X9gt7InFQ1riKMAuJJmdaJI3PhEpEZ/5A2NdZFL6MYoVzsKgmwnAKWAOz4ziwQR2UrBF2n+/B/R8XbCMccLsJSaysPL5/DLL7WXCwdeu146g15NwAYxLBRT4D3wbAriH+09RZ00OE7PI6dlsiEwEnuebEJlnIbCX7bZTOGu4ZSPza+M/EYQj0Atfj0+QBAd1WTNUL3efR2t0xHEM6nu5O7UHI0iNbl/k1xhPYnMZQ2F//FjWZTWQlEzPyaRDnYxCR2NOs5XpxY6oCJd1eO7MplJHYbsgmXWylGMvHzkb8VYLA+SFf08eSi3Fd7QVqIj0RjVzGs/x6igq6QIYMgTQQEaDREBhUsRfbjZOPd4aX/7WtHiPQuiVglhrwbZVtOWAdiaLECbpl2xTXYLpgglg5UOBd80T8ahaEdDT3oupeVa3ZA50i4/kl0cf25KB9NDrm9kUyb7BT3XYN9fxNgSZjIWoI4LNljobR/YftojKcjzh2jzW4iDPYFKmJFkET656lMVYywf1irhwqg5ukkiSSD2wPTOOwRRijj7WlVeYOpwuN25MXMXET0rF/BGwGrL5N7upBEdWhIeHI8ko28CyDDuTTxkQB5AKcN8VTZFEOsNqON3zMPVeNFd0oKIqucNY6ZOQmoUfLJf7x0H4yVJ4EOWnyOEEtpxE2K65r9FAAFs1+bXqledkwRWidudIi/AuAykvVyKoIEZ6cLrlaI3mWlIAC+Izsvxr2pHFspUY1b8z+RgDjm30t2axE6wRyyUC9Kt18fxCPIerxWsfndgM47dqgwgQlO4v2EdUMInZ61IjlLDaAQZhCT02jYn/OnZTheG0i301pZsqrdezFxxnv9LQbAFN373xvYyoCjUKWFEU/Tmerqz59USuyXiEA5dUeaCUPXsLy1X9ST4atwGGvX6ZrVBhT9O9FwDb+97nA6vPQ1nIW3p/Pd5rGzTq5qE+if7jhgkq3GSFvbk7Xr6KEmlGKdgYMP4YbLvWnAHKaow+Ipu8ufX0eIgF/6iLYOjvwLyuJxRSo6HEPHkWSygtxtzgBSSNlrgDhcpkLpIACYyK3cjwWrvx1Kj/t8WAKN66iYpSmco4JreDKHIlOeJ1nr0uag2z6Ffwe7QBnGh6904lAbUnKKHUFSlbCfq/iNc+OnulI2f+W+ZBl90XNYgSE5/Bo03MOO70z6zA4PhA8TvpiP2LPP/XUuY1wWHrPGoHA+dCjsXLj0ffT4h2JflbljLezvSEGAwXNePuZnzdu00/whJu4A6qmQlAlma9XpPZeeyYjCRighY2zEF0Gel8uDuLTczkURHXYsXFxtSh7Wkn3dBFlGCp9jmLf1eIy3o06Yyt10Y9teu0YCi3pENGg1jOqXJ94CeieAuq82OOGSKO2wbJXWulycQJ9O2OdQ/ed4x7I8dWCawO/98xPrPy8to0Mi46y6Io60aD76AVAUGB2Oe64w6sbLARj1yv9f3HovKB2SWZNyV0pVmrt97HIcDs2Y/DAQeEHA7+SeZmc46O4f+16cqg9st+uaFCFzYzzg72PwtOu6SKRV542OQmBxxrrcJx8uijs5TOVWP+ccMhSB6z8qzVJKJINBUVabr3WCvs6Tewk8h+GSE2007ks/cU9A8OFuYBWeUWqlzUGf3Jh0feY/x5ks1gesj+SiaLv6hzy0wllgDY9YW02OFZ0C660Ad5EP+E1jyiKabpvH90X/wGEayY1dHYD1uhErMTf4k9V0fOzc6puJz5KtVN7m24Uc19BgsbPTSifJxwDsIlRnjOwhyJHoLPfdlsGJ+K9SOSQI4RgkTlBmJ+2ysGU0lOsN+/OcK0EC0NDKw1HPNvTZxgT9i5lQkFa7wGSg9sNrEvnoIWB+gPkaad5oTRUmrQu2OSHPdFO3WWeNt4KsmQv405IBo0X9yppl5HG/IL+BHjr2IoGydGPzRTIQoPwTmfQKIPKDCKH72z7Q0OYb9OiXvsd6U17+xont+Vsv0UmyW3Otti5ASHL4gL1lRhdY3MKmNbgFonFgJ9dhDzHghQ0wpOMRJmwy4r+vKQt76po/SBhHd8qN85i5x1UUvlPYnmiJteRlkbvYQlziV7HSSpogS8uwSYT0z4azJHwQetP62g9a+QYNdHxRG5xqQlSSJnVngC3VY7DNAdTsyVPcyoSRIt7rUF11OS/IWHpC7YRxd7wTMww0CUXDnY+bUsj5Dg3au0ol+4yejrQnVAYtyyaQZlU+iJ7VJZnYTUPpUY95d5kpx8IUxPDquS+m3Nhb6q77fkpsY3Vr4D6wqMB85rhvvMCPGqDwObAMqtyhAWPZvknaSd8vVOJ1w9dPaX3zx7I3T3jO2XqgCjw4h2R0uZ+olEPz5vY4GEGJdcEzj+HqDVGdZGf2Y2CVGl6U/FobNGU9jAQmpVLN52LC1ssKPclsS91WrJt6YAGgqop671yCVDBtBWlUz2msUhp6V8zEcxWEe45E9WXGM+PX4tg5Y5vZSbVuWxvELj/Lyg1f4rTZBU4dQgbIspyTeO6a2AINgEL859v8CHVn9uy1wzaxcLCby5MNbJBZsWpSY0es3wXFM8eS1LiP5wrzjzxwrvH8Wcvwa4nLEGJBrmUxE63F5hgHHxVZmP0e7cqYrP33j5QOhGy30pXckxHVyeJkb6cQqvoN57ZH/JbpF6OZsCGxpciPyAFHRIavLuwGTyG3W8DhkNHgIXFRUOtGZV2mNwXzDCCtQua/tJ5n4CzGsyXqbSO/ublkdQ3X48KdDx0qnind6DcCLcTxCP+6dyTneiiDEPE/1ryg+8/Fj5TUFzv0Yoq7zq59II0pV82Ar8LyyRozxh8jIUs+zoB11hgTME3HlFY3Q3U3v+/PEgvDBJJcYBUbAcBLRBO6hTD4X0OOSYmMO5ro3xmQsC0oazRHKHg0125vCHYnh5WtOmFFu1r79YA8HyOAP3qvC78kIRx9wxY9RQPkAC5yUH+x4pl4eFyjFgcza3OeuC964xzco2/CM3aTN6ZGuSeiy0ZtNtd5ns4KaFidovG0OiL+a/F6izg98ainDTXK64Wv0A4q4lzCy0OpIQpfo/yCld7fWBSXgIyZ8XFfcpXOwLxw5hcs0KrhGCuQqmMxhZ9jBBx12GFMIyqo+y95rCc3WSzhNnAAIkqotV0f4haylvjBeZt/Yyj8a5wXLsT4SrmdTbRSkMRuXOWa85CBHdRWENReshWE46xz+/JcgES0cKIq0Cjr9g0e8AckplKz1HpEMN9Wf6BbVMr8v+OUIEVHWny6zdMIDStHW63F04282+IAOXOAqK709fkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQQJERUe -->
