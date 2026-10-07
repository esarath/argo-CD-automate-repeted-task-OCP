# 05 — Advanced Enterprise Design

## Scaling to 100+ teams

| Concern | Design answer |
|---|---|
| Render cost | ApplicationSet generates N Applications; ArgoCD shards them (`ApplyOutOfSyncOnly` keeps each sync cheap). 100+ is routine scale for ArgoCD |
| Git noise | One file per team; PRs touch disjoint folders → no merge contention |
| Heterogeneous needs | Extend team-config schema (e.g. `egress:`, `scc:`, `labels:`) rather than forking the chart — one contract, more fields |
| Blast radius | AppProject caps any single App to the whitelisted kinds — a bad merge cannot take down the platform |
| Templating drift | Chart version bump = `Chart.yaml` only; fleet re-renders on next sync |

## Multi-cluster (hub-and-spoke GitOps)

```
                 ┌──────────────────────────┐
                 │  HUB: openshift-gitops   │
                 │  ApplicationSet (x2 gen) │
                 └─────┬──────┬──────┬───────┘
        cluster list   │      │      │
     ┌─────────────────┘      │      └────────────────┐
     v                        v                        v
┌──────────┐            ┌──────────┐             ┌──────────┐
│ prod-east │            │ prod-west │             │   dev     │
└──────────┘            └──────────┘             └──────────┘
```

* Register spoke clusters as **Secrets** in `openshift-gitops`
  (`argocd.argoproj.io/secret-type: cluster`) or via ACM `Placement`.
* Combine generators: `list` (clusters) × `git files` (teams) — a
  **matrix generator** produces `App(cluster, team)` pairs.
* Destination becomes `name: {{ .clusterName }}`; add per-cluster values
  overrides (e.g. bigger quota on prod) via `valueFiles:` layering.
* Keep per-cluster AppProjects if tenancy rules differ per environment.

## Kustomize vs Helm (and when each fits)

* This design uses **Helm** because onboarding is fundamentally
  *parameterised* — values-in → manifests-out.
* Use **Kustomize overlays** when per-environment deltas dominate
  (`base/` + `overlays/dev`, `overlays/prod`) — e.g. for the bootstrap/
  layer or cluster-specific policy.
* Common enterprise pattern: ApplicationSet renders Helm, and for
  multi-env assets, helm chart is referenced from kustomize `helmCharts:`
  inflation so overlays can still patch.

## DR / backup

| Layer | Strategy |
|---|---|
| Git repo | The *desired state* is the backup. Git mirror to second remote (or Gitea/ADO) |
| ArgoCD config | Back up `openshift-gitops` namespace objects + cluster-registration secrets; or rebuild — everything is re-derivable from git + bootstrap/ |
| Applications | On DR cluster: `oc apply` bootstrap + appsets → the fleet self-reconstitutes from git. This is the core DR argument for GitOps: **recovery = redeploy git** |
| etcd | Standard cluster backup still applies for non-git-managed state |

## Audit & compliance

* **Change attribution**: git commit SHA ↔ PR approver ↔ ArgoCD sync event
  ↔ API audit entry — a complete, queryable chain.
* **Policy-as-code evidence**: `validate_team_config.py` history shows
  enforcement; the AppProject is a declarative compliance boundary
  auditors can diff.
* **SoD**: developer proposes (PR), platform approves (CODEOWNERS), robot
  applies (ArgoCD) — three separate identities, no shared credential.
* **Retention**: git history + ArgoCD's `application` events + OCP audit
  logs; ship to SIEM for regulated environments.
* **Quarterly access review**: `oc describe rolebinding -A -l platform/team`
  gives a fleet-wide access report generated from live state.
