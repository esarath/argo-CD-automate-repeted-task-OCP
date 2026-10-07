# 02 — OpenShift GitOps: Install, Configure, RBAC, Projects

## Install the operator

```bash
oc apply -f bootstrap/00-gitops-operator-subscription.yaml
# wait for it
oc get pods -n openshift-gitops -w
```

The operator creates a cluster-scoped ArgoCD in `openshift-gitops` with
OpenShift OAuth already wired (Dex `openShiftOAuth: true`) — log in with
the **LOG IN VIA OPENSHIFT** button; cluster-admins are ArgoCD admins.

## Grant ArgoCD cluster-level rights

The default instance can only manage `openshift-gitops`-adjacent namespaces.
Creating team namespaces requires a ClusterRole — deliberately scoped to
exactly the kinds the chart produces (no `*`):

```bash
oc apply -f bootstrap/01-argocd-cluster-rbac.yaml
```

Grants: `namespaces`, `projects`, `resourcequotas`, `limitranges`,
`serviceaccounts`, `networkpolicies`, `rolebindings` — to the
`openshift-gitops-argocd-application-controller` SA only.

## The tenancy boundary: AppProject `platform-teams`

`bootstrap/02-appproject-platform-teams.yaml` enforces:

| Control | What it does |
|---|---|
| `sourceRepos` | Only this repo may feed Applications — a PR can't point an App at `evil.example.com/charts` |
| `clusterResourceWhitelist` | Only `Namespace` — teams cannot create CRDs, ClusterRoles, PVs… |
| `namespaceResourceWhitelist` | Exactly the 5 kinds the chart produces — nothing else lands |
| `namespaceResourceBlacklist` | `Secret` denied — onboarding never writes secrets via this path |
| `destinations` | In-cluster only; no external clusters |
| `roles` | `platform-admin` (cluster-admins) full control; `auditor` read-only |

This is the difference between "ArgoCD deploys YAML" and "GitOps with
multi-tenant controls": even a merged-but-malicious team-config is bounded
by the project. Together with the chart's reserved-namespace check and the
CI validator, three layers would have to fail before a team could create
`openshift-*` or a ClusterRole.

## RBAC summary (who can do what)

| Actor | Permissions |
|---|---|
| Developer | git push to `teams/` only (enforce via GitHub CODEOWNERS/branch rules) |
| ArgoCD controller SA | The ClusterRole above — nothing more |
| Cluster admin | ArgoCD admin via OpenShift SSO; AppProject `platform-admin` |
| Auditor | `platform-auditors` group → read-only on platform-teams Apps |
| Team (in their ns) | `admin`/`edit`/`view` RoleBindings from team-config |

## Recommended hardening (production)

* **Branch protection on `main`**: require PR + 1 approval + green
  `Validate` checks; require review for `teams/` via CODEOWNERS.
* **Repo credentials**: read-only deploy key or GitHub App for ArgoCD —
  never a write token.
* **Webhook**: `github.com/<org>/<repo>` →
  `https://openshift-gitops-server-openshift-gitops.apps.lab.ocp.local/api/webhook`
  for instant sync (else ~3 min poll).
* **argocd-rbac-cm**: keep `users.anonymous.enabled=false`; use SSO groups.
