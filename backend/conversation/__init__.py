"""Stage 29 — Conversational Factory Intelligence (research §40).

Three deliverables, all free/local (Groq→Ollama, Rule 9) and HONEST (abstain over invent):

  * `ask`             — G-022 "ask the factory": grounded operational QA + "why did X happen?" answered ONLY from
                        real evidence (Art-12 signed decision traces + Stage-28 GraphRAG + live sim/KPI), with a
                        Verifier-style honest-empty when no evidence grounds the question.
  * `nl_inject`       — G-023 NL problem injection: NL → a strict Pydantic `InjectedIncident` (validated, re-ask on
                        failure) → the SAME validator-gated self-healing loop (Hard Rule 3: the LLM never actuates).
  * `active_diagnosis`— G-026 active diagnosis: an information-gain (entropy-reduction) probe policy that
                        interrogates a suspect agent (`diagnose.request/report`) BEFORE committing to intervene
                        (KB_25 §1b), Bayes-updates its belief, and commits OR abstains — misdiagnosis is a recorded
                        outcome, not hidden.
"""
