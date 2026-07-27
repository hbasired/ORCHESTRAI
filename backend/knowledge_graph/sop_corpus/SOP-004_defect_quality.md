# SOP-004 — Defect Detection & Quality Gate

Applies to: quality inspection of produced units at a stage.

Procedure:
1. The defect classifier (ResNet18 transfer-learned on NEU-CLS) scores a surface image into a defect class.
2. A confidence below the acceptance threshold routes the unit to manual review, not automatic rejection.
3. Rising defect_rate_effective at a stage correlates with tool wear and crack proximity — check SOP-001.
4. If the classifier model is unavailable, the honest state is "defect classification unavailable" — never a
   fabricated class or confidence.

Related equipment: inspection stages, the defect_classifier model.
