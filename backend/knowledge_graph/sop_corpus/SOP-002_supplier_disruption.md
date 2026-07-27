# SOP-002 — Supplier Disruption & Material Shortage

Applies to: Enterprise (supplier) nodes feeding a MaterialClass (SKU) consumed by a stage.

Procedure:
1. On a supplier failure-rate spike (observed failed/fulfilled >= 0.5), quarantine the supplier: the Contract-Net
   coordinator stops awarding to it.
2. On a delivery-latency spike (overdue-pending orders past a 3.5-sigma age), raise a supply-chain incident.
3. Re-plan via the Contract-Net protocol: sealed-bid award to the least-cost eligible supplier; every award is
   safety-gated by the supply_chain_order contract and written to the signed audit chain.
4. If a stage buffer starves (persistent queue_depth == 0), that is a stockout — expedite replenishment.

Related equipment: Enterprise supplier nodes, MaterialClass SKU nodes, the fed WorkUnit stage.
