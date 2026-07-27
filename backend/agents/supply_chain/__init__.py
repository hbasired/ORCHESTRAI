"""Stage 26 — multi-agent supply-chain automation layer (KB_25 N-domain extension).

Five role agents (demand / inventory / scheduling / logistics / supplier) coordinate through a deterministic
Contract-Net protocol (research §37.1) over REAL SimWorld signals + the Neo4j ISA-95 graph; a disruption monitor
raises incidents into the runtime via the Stage-25 exactly-once router. Every CFP/award is audited (signed
audit_chain rows) and every order effect is safety-gated (Hard Rule 3). No fabrication anywhere: agents bid from
observed statistics and real model outputs, degrade honestly, and never invent a number.
"""
from agents.supply_chain.consensus import ContractNetCoordinator, Cfp, Bid, Award
from agents.supply_chain.orchestrator import SupplyChainOrchestrator

__all__ = ["ContractNetCoordinator", "Cfp", "Bid", "Award", "SupplyChainOrchestrator"]
