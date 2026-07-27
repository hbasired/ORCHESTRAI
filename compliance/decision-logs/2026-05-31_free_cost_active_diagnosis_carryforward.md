# ADR — Free-cost constraint, active diagnosis, and carry-forward of new concepts (2026-05-31, run 4)

**Status**: accepted
**Stage**: cross-cutting (constraint + process + capability)
**Author**: agentic-governance-engineer + system-designer (Claude session, 2026-05-31); operator-directed
**Related**: KB_25 §1b/§1c, CLAUDE.md §4 rules 9–10 + §6, tasks/TASK_TEMPLATE.md, memory feedback_free_cost_groq, gaps G-026/G-027

---

## F1 — Zero paid cost through the final stage; Groq free tier default

**Context.** Operator will supply a free Groq API key and requires all implementations to be free-cost until the
final stage.

**Decision.** Hard rule 9 (CLAUDE.md §4): every stage uses free tier / OSS / local only. Default LLM = Groq free
tier (`default_llm_provider="groq"`, `GROQ_API_KEY` in `backend/.env`, gitignored) + Ollama (local) fallback —
the code already defaults to this. Real HSM / managed cloud / paid APIs are post-final-stage/pilot items. Keys
never committed. Reinforces PRD §0 ("zero paid SaaS"). Engine reasoning (causal/neuro-symbolic/planning) must
fit free-tier limits (small/cached/batched prompts). Gap G-027.

**Why.** OSS wedge + the operator's budget; a paid dependency breaks both the pitch and the constraint.

## F2 — Active diagnosis (predict can be wrong)

**Context.** The head agent must not blindly trust a prediction; it should interrogate the suspect agent and
reason over the response.

**Decision.** KB_25 §1b: the coordinator sends `diagnose.request` (run a named self-check) to a suspect agent,
receives `diagnose.report` (result + health vector; timeout ⇒ that agent is the fault), and reasons to
confirm/deny the prediction before verifying+intervening; a healthy result widens the probe / revises the world
model. Two new agent-message types added to KB_06. Misdiagnosis is a learned outcome. Closed-loop, self-
correcting. Gap G-026 (Stage 11 + KB_06).

**Why.** Prevents unnecessary interventions from wrong predictions; matches the operator's "check the specific
agent, reason, find the solution" requirement.

## F3 — Carry the new concepts into every future stage

**Context.** Many new concepts were added (system design KB_24, self-healing engine KB_25, dynamic features,
N-domain, free-cost). Operator wants every next/future stage to implement *with* these, not bolt them on later.

**Decision.** Hard rule 10 (CLAUDE.md §4) + §6 invariant: every stage (Stage 4+) MUST read KB_24 + KB_25 +
`audits/OPEN_GAPS_LEDGER.md` and fold the gaps targeted at it into its acceptance criteria. `TASK_TEMPLATE.md`
now opens with a mandatory "Cross-cutting requirements" checklist (read KB_24/KB_25/ledger; pull in gaps;
free-cost) so every newly-seeded task doc inherits it.

**Why.** Without an enforced carry-forward, recent architectural changes get lost between stages. The template +
hard rule + gaps ledger together guarantee each stage builds the new concepts in as it comes.

## Risk register references
- Reduces "architecture drift between stages" and "theatre" risks; free-cost reduces budget risk.
- Free-tier LLM limits are an execution constraint on the causal/neuro-symbolic engine — mitigate with caching/batching.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: wv6se+HmhQoi2WrH3FUbaHUwH3vcUowB8gf66iJD5qnzYGrolRD4ICN7g6eSGezgk3OqWhu7TzmHQ4uqQwOZ+CuBJVzEq7V/sEqW5QH18o8RYRlqWZr5mpynjgbLT98a2io7qp1TA3na4ug94YaBd5jooPOXMmGPKxk7AzB6KCcP7SSPyR3hASGeaAHdFv9SWRGO2wbviwaWhOCc1USR/C04QIDwwHJjNoMRNALZMo7CsUllfB/mv9QjI7t65/CHbzKGZ1PEWWDtAH6xM0Bry4jUSyiDa/hBCpl2bWh7Pj632gtww/TIbaYD9p3Uz8m/aXvQk2FT30y8nN/8CIsMUvDSjy1K91T7m+NoRuiiC1BuLzbtJDAcLTUr+QbV2CgOt2fXaNRJSssLoJcvDMl1dbgvxc+u36JYPS/ANwtzqDFzg5ipYC6FW93C1u3lZ5AG5W9Ux0z1RUHEc+vi7+KymJ4d8EO0sQ5gxW+JlIWmyrrNSPxAf9hexEHzt6zRNPORMrUeFy2wskFyRg3qi7Y+pld+ceptKU2o9/uVurMKe2LruFm9Nn2/Om9Xqhnv12Q+APfB29zNRMWm9IJkjDQF1S3619yutmKbnVqLX5OPgvdxphRbcNFE6b2KTiVxKLG1M2WlXd3clMYX/88SKQXVvFMVcR5hU3mBs/CuJrG1/drytfrw3LgB2dA2BqQqnTcPtH2Z+ij4ZAvG8KYMErJ/gjl4l9QshRnNkOUqX+IPTuhY7EMDkpa7Iqc845n9waAFdx9+YIp6A6A3K+fBFW+QOEEdiu2LVIWCEk/EiUNfZLiPutLm+l9RUCS5AKoddh4YnKGq9IBsQK7PVWQGVEcXlRIV1LzA/BMQq0K9DBg5JLNz3uVHggybt7Uen8IYS1ZnjZZa2egawZcmRXDCrfg4CCwbNazNejynULeq+D+Ae8xEpHiCoD0RDLje720qnypB780ETI6iLNbsKCVeD5DCg2AjxAhIoiRCEbtirVKVDGo8Tdf/jObODRtzm8CLAEWgTGl74ZR3Ru23bziiB1LuCZbNMtkbKxHfxP/vNmprpGH2qivsToCa4Tt10DWfYm+cCwU969b4oLmbPmbVX0wqKjnQHs7WhPkBUXOazqfmQtqL+rr0mL6hx7QZRCXAMsmhbbM4sGx9oDvFV4QMxjZPLnH2btoLQCshEA+d3VLNE1U7Lm1oGgQIY930RX2mgpvp4j0+VXMTwzhRCf35660r7P4eyE4eGwhIDGz1uu4ges+uRBE9sIoP87olCFQfqWKOARdO8atzC8wkArDL6m0k3HiZFFHgq4m3xIkFud+EItf7s+9EanmOXERbyd8fZLH3PZoVD/Nklo4vug3nhMbataZ9sE8pOnuf0tQKx7wHfECIZyIIGfmVu7pa0NBusRcGC549XQwBVcAgJIORmSPLXjCJr5q0+BrWYgF47Pdo+bUlwl6AWayDh8V7PD3OL5noY/r4LfpKyRHo/3SUtWJqRAmf2XwbQ9/uepKVoRqv1zQtxGfCKwKiSY/5UHFuWkYmxM1R6UzvFTGevjKLmGKOmh/GjKlhUQEBVFReU4hyHn758MqcXk1/6HZf+wXxcWO5b/uPFZ7ZFN6iw+HFoHrTqQCzm5vHizX4GfFjo1/9WTQY+claqjJVLuf+2fO2ueii+ditps3h0RSEqm6GlJuRl9qUtYGO2mOEjrpiSL5T/YvqBresjeky+tiPTljTKD84Dldfc8uNDX1HmJ6pXWWsFAvoYsWTi3MjUk1hfLM50E1e572PKaw0Zyg9yn3VbvL00eX8c2ZvCJ+VNS99Mxc42mMcEWD/p++U00w2wGItkR7DMmUA6rIXtPX3bUYIXnFI99UU8CLzfJpBUfbZ8h18O+tEWuLIOI0NRenh5yZfH7fHO3aqGvpdyIts7XSNGYuOfCXPRnV28IS4E+Hi5N8B9CKPjQxnMzwA0h9vnQBkBZ3e39i4eDbcumjrIHnt2vIAW06Yv6zezc+dGtiT9e++SoRSbk78SYkAfHn983O6G3sySEwELCZxLbIkN5g+xy6VPj1BXnT6N99KRFh/ZTp/XQKRBs+zp8FXY7WWxfi5o3xhXYkZBccJ6Ie5rRFf4BgG/NBbTC4eUhkndPxaPWY8c0rnstOPBqwq4UInCKu/+O4yR0K2ZY659Rx/HlF+IcVujx97BiLljFfUtAFYoYW7Xi9XIwOwx7L2mQ9wLVHH1D5vDyX2jGNDa7XmjtV8mSMbM+tbRyyJDNqWZGFmXMAtXBKS0nG6rQi6Y2H6MStxIUCV9Y5WTqvxlaM09xdsvsHxcUeBQ1Cth11+VnB/TEjSGHS7ptKMaQJFiLinLqv1nYNmv5QF8gM5Z83TVCSKpGX2UcqjexdB68fhEBcywPT+A6ilfZ+EGaDiA1kuyYdBRkqbB0rjq+rbj42cKHHq3Ku1AnBt9GnGsqA4TnwWGJJVoaZuhPVPaUOc/kI8UXHlX4C9j3A4enam/zFFth+2JAz1qqa/G+4TG1IYXny1bQwZs14MpO0nBXJqr9k6zbHa85jDMWuLhbNncQhRTQebJKqj69umrZcvMtDFZXIclSQdfMk2ElJzbZT9Pihw/VPASgdP6KhHtTdphfFVwF1vtdLcBaF25d6oog6Tq+/waUXPb5LnlemfPoqrfMqVGFe3jcb5Qs/f85SxPZyRRx9/4a8YHnQheryO6J0ZZzUxyXG7J/lzFDNW0r3Pj8Iop9wEfrdJ27yG/diQ2GlX3+3PeG3NSBCDkK9fWZeeCUal0EZ1Akjfhcgq9RDgie5jHKLb3HbL/dWef/z4A10AY+uAk9JsPMWSwf90rmbV0B0LRhvnRw7rrbS0pWRTW36RXKrHygKfD20PZ2Vc3gkMNELY053/VbqfagCnTmM0X7s+v4tYfaWrv/dEdyYi4w1IpsJ3QGJcunato+wSC0USdLs15QJiN3ry4Vev76bPjAldlNoGHhqcU4CtfCAHQcXf2BujwJUq/M2zPnfqAWnaPtBhWoaY0XLlcyQtF8SSkbkj+qy057Rt0lJSf06vgQIvupoDwYA0kSCaRvSSkevODbXxKPE56pu7SESkVlgIuHN8KuDgGEE7BS3ASJ3F3YrafiHEgVl2XHO8/WnQlQk4tq/c77/BZg2b7SHrfKw+G0swGpHwy6FrPBlVgyvhlv88xd/QkufowyZmoAuiRRFmpVi8QZUJwsVJCfNTFtiF7eOi/qIPOzzvlL8r4OBbHgcG6jsd9O/H26McbMI9W5YeKTUmNTFzwEqxNf4YA0u8P/kwYWZ8ntB61xwM0LPCvYGFqvpPCYJ9ip5FZtUV24gYM0wcXfv66uA1JjfljgnxR4W1chFQ80uunZR1zzveUwN28Qm5LuuHE5eNZUxnrwtK1heJke8/yVAOLM+aeytB6vsgkn4XSWJ5Y7NLQW3Aka/b+mo/R8SCbu5+PKw93UvL7I8qwvGHeZw7jldif3u7fSwWKZFbtOP5QllkgHrz0m6bt6Ro1A7gSP/vJnPs6GBynaiH33Q+9E5XRZAVIuYrcEnLfC/TOBE66bt/Ct543aB/x/TdErCNcUOXZT45cwTh0hXoI1yun1raYE7zK5ujOjDfn3vOtitke7ZLrKtuG1mEHbN84PT8eJ6BWOOAjODsTGIiTsOtQNWoaOcTiKl5fjulbi5h7/uCdbnPxB/l8BwTce7lxsDUNWzv6oRAFAN5/mEn3HBo52ORvY/RO7IkSzMaLD1DzEYahs+SsreuiIXDTfdSdeDGPq3PdHJeyT1gXhkaMXTQuYdHCQpsYMUF5qlMouIsNDuuCEtnho3p501v+ilYLQD5VWp2FSwqr5nbQlq7PJeieogwVm7swaoNFZG+tAXmWxEjo2Bb0BxlefKOqiimckjo7f2hG0b6/MRwioOykMc774UoMzkJZN51qjbNaH2Krv7UkncuKkoE3Zb6EKuQMnU4t1XZt0/AkHctUYuYz8MhyMsHc9+hPIug8nXpSCO4yQdPaBfdW9jJO2N7Q2cxVPwcQmkPTiVEr1M8uWaWXMMHYPcJ8a8gAwk1CHjifAzGhuXslv7pzrkWika6A3/vUYcOeo5wIYjL3MjuxaZjMTz4XUSYUmnIMyjK1VGHpfwM/YI7nV2GKctmVw7Zo9AQzsqv8MBEsl5Bmh+hEEtgj5kowTvmJnxCg3n338ZxqdwqgEsJR3tTcE8CCMsSvRsjHgnzh211OD4CYmYKToItbtRl375ainc8HoBx+Tag4ldWgSaxZuufSHjZsrZsgQ1KipDz9QsNTYrsik/oPX34hPBdL3VVE/eaGAC49CUee9Glcs9Uenl+9YECDgAgwOSZO9FIh4ias7cECxsrS0xmmbzIKM7R9gNzg44gUmR+usLV5OkWZHuuztDR4eIAAAAAAAAAAAAAAAAABhAUGCEq -->
