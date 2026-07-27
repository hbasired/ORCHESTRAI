"""Stage 13.5 — post-quantum crypto (KB_13).

Real FIPS-204 **ML-DSA-65** signing behind a pluggable **KeyProvider** abstraction (PRD v2.1 §v2.1.5): callers
(`pqc_signing`, `audit_chain`, A2A agent cards) depend ONLY on the abstract `KeyProvider` + `get_key_provider()` —
never a concrete backend — so a purchased HSM replaces the software signer as a CONFIG change (`CRYPTO_PROVIDER`),
not a code change. Software backend = `dilithium-py` (pure-Python FIPS-204, Windows-native, no liboqs build — the
dev/no-budget tier; production swaps to `pkcs11`/`vault`). No classical pre-quantum signature algorithms (the KB_13
forbidden list) are used in new code here.
"""
