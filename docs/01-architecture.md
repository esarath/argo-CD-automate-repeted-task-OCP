# 01 — Architecture

## Repository structure and why each directory exists

```
argo-CD-automate-repeted-task-OCP/
│
├── bootstrap/                     # One-time PLATFORM setup, applied by an admin.
│   ├── 00-gitops-operator-subscription.yaml   # Installs OpenShift GitOps
│   ├── 01-argocd-cluster-rbac.yaml            # What ArgoCD is allowed to create
│   └── 02-appproject-platform-teams.yaml      # Tenancy boundary (AppProject)
│        # Exists because: bootstrap is infra plumbing, NOT day-2 config.
│        # It is applied once imperatively — it bootstraps the thing that
│        # then manages everything else. ("Who watches the watcher.")
│
├── applicationsets/               # ApplicationSet definitions.
│   └── team-onboarding-appset.yaml
│        # Exists because: ApplicationSet is the *discovery engine*. It scans
│        # teams/ and generates one Application per team folder — this is what
│        # removes "create an ArgoCD app" from the manual runbook.
│
├── charts/                        # Helm charts = parameterised templates.
│   └── team-onboarding/           # THE definition of a team namespace
│        # Exists because: 6 resource kinds × N teams should not be N×6
│        # YAML files. One chart + per-team values = single source of truth.
│        # A platform change (e.g. new baseline policy) is one chart edit
│        # that rolls out to every team consistently.
│
├── teams/                         # The self-service surface.
│   ├── _template/                 # Copy-paste starter (example file, ignored
│   │   └── team-config.example.yaml    by the generator — see note below)
│   ├── payments/team-config.yaml
│   └── analytics/team-config.yaml
│        # Exists because: developers should only ever touch this directory.
│        # Folder = team = namespace. Nothing else to learn.
│
├── .github/workflows/             # CI gates.
│   ├── validate.yaml              # PR checks: yamllint, schema, helm, kubeconform
│   └── deploy.yaml                # post-merge: render check + ArgoCD webhook nudge
│        # Exists because: "merge = deploy" must be guarded. CI is the only
│        # reviewer that can mechanically prove a PR is renderable and legal.
│
├── scripts/
│   └── validate_team_config.py    # Policy-as-code on team-config.yaml
│        # Exists because: schema catches syntax; this catches policy
│        # (reserved names, quota sanity, defaultDeny cannot be off).
│
└── docs/                          # Design docs, runbooks, interview notes.
```

## Component design

| Layer | Component | Role |
|---|---|---|
| Intent | `teams/<name>/team-config.yaml` | Declarative desire: "team X exists with these limits" |
| Discovery | ApplicationSet (git **files** generator) | Turns each config file into an Application — new folder ⇒ new App, no human step |
| Rendering | Helm chart `team-onboarding` | Values → concrete Namespace/Quota/LimitRange/NetPol/RBAC/SA |
| Tenancy boundary | AppProject `platform-teams` | Whitelists source repo, resource kinds, destinations |
| Enforcement | ArgoCD controller + cluster RBAC | Applies manifests; `selfHeal` reverts manual drift; `prune` offboards on folder delete |
| Gatekeeping | GitHub Actions + `validate_team_config.py` | Blocks bad/unsafe configs before merge |

## Why ApplicationSet git **files** generator (not directory generator)

* Directory generator sees only folder names — values would have to live in
  per-team overlays/Kustomize. Files generator **parses the yaml content**, so
  `teamName`, `quota`, `admins`… become template parameters directly. The
  developer writes one small file; the platform does the rest.
* `teams/_template/` uses `team-config.example.yaml` (not `team-config.yaml`)
  so the generator ignores it — it is documentation, not a real team.

## Sync semantics (production-ready defaults)

* `automated: {prune: true, selfHeal: true}` — merged git state is enforced;
  manual `kubectl` changes are reverted; deleting the folder deletes the team.
* `ApplyOutOfSyncOnly` — avoids full re-render churn on large fleets.
* `retry` with backoff — transient API failures self-recover.
* `ignoreDifferences` on Namespace — OpenShift injects SCC/SA annotations;
  without this the App would flap OutOfSync forever.

## Diagram

```
┌────────────┐   PR    ┌──────────────────────────────────────────────┐
│ Developer  ├────────>│ GitHub repo                                   │
└────────────┘         │   teams/payments/team-config.yaml             │
                       └──────┬───────────────────────────────────────┘
                              │ pull_request
                              v
                       ┌──────────────┐   green   ┌─────────┐
                       │ GitHub Actions│──────────>│  merge   │
                       │ validate.yaml │           └────┬─────┘
                       └──────────────┘                │
                                                        v
                              ┌──────────────────────────────────────┐
                              │ ArgoCD (openshift-gitops)             │
                              │  ApplicationSet ──> Application       │
                              │  (per team)     renders helm chart    │
                              └──────────────┬───────────────────────┘
                                             │ apply (project: platform-teams,
                                             │        rbac: ClusterRole)
                                             v
                              ┌──────────────────────────────────────┐
                              │ OpenShift api.lab.ocp.local           │
                              │  ns payments: Quota LimitRange        │
                              │  NetPols RoleBindings [SA]            │
                              └──────────────────────────────────────┘
```
