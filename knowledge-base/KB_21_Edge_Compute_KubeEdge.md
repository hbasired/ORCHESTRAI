---
name: Edge Compute via KubeEdge (Cloud-Edge Continuum)
description: KubeEdge (CNCF graduated project) for offline-autonomous edge deployment; ArgoCD GitOps; MLflow model registry. Added 2026-05-24 in response to Project Aether gap analysis.
type: spec
last-updated: 2026-05-24
---

# KB_21 — Edge Compute via KubeEdge (NEW — 2026-05-24)

## Purpose

PRD v1/v2 specifies Docker Compose for local dev + Cloud Run / Fargate for production. That is correct for the cloud side but underspecifies the **factory-edge runtime**. Industrial customers need:

1. Local-server inference at single-millisecond latency (Stage 17 safety wrapper requires this).
2. Offline autonomy — factory must keep running when WAN is down.
3. Resource-light footprint (NVIDIA Jetson-class hardware).
4. Cloud-edge consistency via the same Kubernetes API surface.

This KB specifies the **cloud-edge continuum** using KubeEdge (CNCF graduated project — the standard for K8s at the industrial edge).

## Source of truth

- KubeEdge official docs + GitHub (CNCF graduated 2024-Q4).
- Project Aether report § 5.1 (operator-supplied 2026-05-24).
- WWT "Edge AI Kubernetes: An Enterprise Blueprint" (2026).
- KubeEdge production deployment data: 100,000+ edge nodes across 29 Chinese provinces / 500,000+ edge applications.

## Body

### Architecture

```
                    ┌────────────────────────────────────┐
                    │           CloudCore                │
                    │  (deployed in GCP / AWS / Azure)   │
                    │  - Cluster API server              │
                    │  - Global orchestration            │
                    │  - Heavy training workloads        │
                    │  - Langfuse + Phoenix + audit_chain│
                    └──────────────┬─────────────────────┘
                                   │ TLS (ML-KEM-768 + X25519 hybrid;
                                   │ Stage 18 mandatory)
                  ┌────────────────┴────────────────┐
                  │ EdgeCore (NVIDIA Jetson / x86)  │
                  │  ~70 MB memory footprint         │
                  │  - Edged (pod manager)           │
                  │  - EventBus (MQTT bridge)        │
                  │  - DeviceTwin (sync local OT)    │
                  │  - MetaManager (offline cache)   │
                  └────────────────┬─────────────────┘
                                   │
                       ┌───────────┴────────────┐
                       │ Local containers:      │
                       │ - LangGraph runtime    │
                       │ - MCP servers (Stage 11.5)
                       │ - VDA 5050 master      │
                       │ - OPC UA client/server │
                       │ - Sparkplug B node     │
                       │ - Safety wrapper       │
                       └────────────────────────┘
```

**Key properties:**

- **Offline autonomy.** When WAN to CloudCore is down, EdgeCore continues running pods. Local LangGraph runtime keeps making decisions; audit_chain rows accumulate locally and sync on reconnect (with ML-DSA signatures intact — rows are signed at write, not at sync).
- **Footprint.** KubeEdge ~70 MB vs standard K8s hundreds of MB — fits on Jetson Orin Nano (8 GB) alongside the safety executor.
- **Cloud-edge consistency.** Same Kubernetes YAML manifests; same Helm charts; deploy once, ship to either runtime.

### Why KubeEdge (not k3s / KubeVirt / SUSE Edge)

| Alt | Trade-off |
|---|---|
| **KubeEdge** ← chosen | CNCF graduated; explicit offline autonomy; ~70 MB; production references at industrial scale |
| k3s | Smaller but no native cloud-edge sync; manual reconciliation logic needed |
| KubeVirt | Optimised for VMs at edge, overkill for containers |
| SUSE Edge | Proprietary tier; conflicts with our open-source-only policy |
| Microk8s | Limited offline-autonomy story |

### GitOps via ArgoCD

CI/CD via GitHub Actions builds the images and pushes them. Deployment is **declarative via ArgoCD**, NOT via `kubectl apply` from CI.

- **Manifests** live in `deploy/argocd/applications/*.yaml`.
- **Image tags** in those manifests are updated by a separate `image-updater` ArgoCD plugin watching the registry.
- **Rollback** is a git revert; ArgoCD reconciles automatically.
- **Edge deployment:** ArgoCD has an EdgeCore-aware sync mode (KubeEdge Cluster API).

### MLOps via MLflow

DVC (Stage 1) + MLflow (Stage 19+) cover the model lifecycle:

| Concern | Tool | When |
|---|---|---|
| Dataset versioning | DVC | always |
| Experiment tracking | MLflow Tracking | from Stage 4 |
| Model registry | MLflow Registry | from Stage 19 |
| Deployment promotion | ArgoCD watches MLflow Registry stage tags | from Stage 22 |
| Drift monitoring | Arize Phoenix + custom prometheus alerts | from Stage 20 |

### Roadmap impact

- **Stage 22.5 (NEW — Edge Deployment / KubeEdge):** insert between Stage 22 (Pilot deployment runbook) and Stage 23 (Conformity dry-run). Acceptance criteria: CloudCore deployed on GCP/AWS/Azure; one EdgeCore on NVIDIA Jetson (or x86 stand-in); Stage 17 safety wrapper container runs offline for ≥24h after WAN cut; ArgoCD sync re-establishes cleanly after WAN restore.
- **Stage 1.5 hooks (post hoc):** add `deploy/argocd/applications/*.yaml` templates as part of the Workstream-B orchestration scaffold; populate fully in Stage 22.5.

### Standards adopted

- **OCI image spec** — all containers OCI-compliant; supports both runc and crun runtimes.
- **OPA Gatekeeper** — Kubernetes policy enforcement (complements our policy DSL from Stage 19).
- **Helm 3.x** — chart format for all deployments.

### Risks

- **ArgoCD compromise** = control-plane compromise. Mitigation: ArgoCD itself behind SSO + mTLS; ArgoCD-to-cluster traffic uses Stage 18 PQC sidecar.
- **EdgeCore device-twin desync** under prolonged WAN outage. Mitigation: bounded queue with backpressure; if queue exceeds threshold, edge degrades to "safety-only" mode (Stage 17 validator continues; non-safety actions queue).

## Last verified

2026-05-24, devops-sre + agentic-governance-engineer review. No `deploy/argocd/` directory exists yet — Stage 22.5 ships it.
