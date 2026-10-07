# 00 — Execution Guide: First-Time Setup to First Team Onboarded

This is the **only document a new engineer needs to run the platform**.
Every step says *who* runs it, *where*, the *exact command*, and the
*expected result*. If a step's output doesn't match — stop and check the
[Troubleshooting](#8-troubleshooting) table before continuing.

> **Time budget:** ~20 min for Phase A (one-time, platform admin).
> After that, onboarding a team is ~5 min of developer time.

---

## Roles — who does what

| Phase | Actor | Access needed |
|---|---|---|
| A. One-time bootstrap | **Platform admin** | `oc` login as cluster-admin on `api.lab.ocp.local` |
| B. Onboard a team | **Developer** | push rights to this GitHub repo — **no cluster access needed** |
| C. Verify / operate | **Platform admin or team lead** | `oc` read access, or just the ArgoCD UI |

---

## Phase A — One-time platform bootstrap (admin, ~20 min)

Run everything in this phase from a workstation where `oc` is logged in as
a cluster-admin:

```bash
oc whoami --show-server   # must print https://api.lab.ocp.local:6443
oc whoami                 # must be a cluster-admin user
```

### Step A1 — Get the repo

```bash
git clone https://github.com/esarath/argo-CD-automate-repeted-task-OCP.git
cd argo-CD-automate-repeted-task-OCP
```

### Step A2 — Install the OpenShift GitOps operator

```bash
oc apply -f bootstrap/00-gitops-operator-subscription.yaml
```

**Wait for it** (2–5 min; the operator pulls images and deploys ArgoCD):

```bash
oc get csv -n openshift-operators | grep gitops      # PHASE: Succeeded
oc get pods -n openshift-gitops                      # all Running
```

Expected pod list (names vary by version): `openshift-gitops-argocd-server`,
`...-application-controller`, `...-repo-server`, `...-redis`, `...-dex-server`.
**Do not continue until all are Running/Ready.**

### Step A3 — Grant ArgoCD cluster-level permissions

ArgoCD can't create namespaces until you allow it:

```bash
oc apply -f bootstrap/01-argocd-cluster-rbac.yaml
```

Expected: `clusterrole.rbac.authorization.k8s.io/gitops-team-onboarding-manager created`
and `clusterrolebinding.../gitops-team-onboarding-manager created`.

### Step A4 — Create the tenancy boundary (AppProject)

```bash
oc apply -f bootstrap/02-appproject-platform-teams.yaml
```

Expected: `appproject.argoproj.io/platform-teams created`.

### Step A5 — Turn on automatic team discovery (ApplicationSet)

```bash
oc apply -f applicationsets/team-onboarding-appset.yaml
```

Expected: `applicationset.argoproj.io/team-onboarding created`.

Within ~3 minutes ArgoCD discovers every `teams/*/team-config.yaml` and
creates one Application per team:

```bash
oc get applications -n openshift-gitops
# NAME                  SYNC STATUS   HEALTH STATUS
# payments-onboarding   Synced        Healthy
# analytics-onboarding  Synced        Healthy
```

```bash
oc get ns payments analytics          # namespaces exist
oc get quota,limitrange,netpol -n payments   # guardrails exist
```

**Phase A is done. Nobody touches the cluster again for onboarding.**

### Step A6 — (Optional, recommended) Webhook for instant sync

Without this, ArgoCD polls git every ~3 min. To make merges instant:

1. In GitHub → repo **Settings → Webhooks → Add webhook**:
   - Payload URL: `https://openshift-gitops-server-openshift-gitops.apps.lab.ocp.local/api/webhook`
   - Content type: `application/json`; events: `push`
2. In repo **Settings → Variables → Actions**, create `ARGOCD_WEBHOOK_URL`
   with the same URL (used by `deploy.yaml`).

### Step A7 — (Recommended) Protect `main`

GitHub → **Settings → Branches → Add rule** for `main`:
- ✅ Require a pull request before merging
- ✅ Require status checks: `YAML lint`, `Team config schema + policy checks`,
  `Helm lint + template render`, `Rendered manifests vs Kubernetes schema`,
  `ApplicationSet sanity`
- ✅ Require review from Code Owners

This is what makes "merge = safe deploy" true.

---

## Phase B — Onboard a new team (developer, ~5 min)

Run from your own workstation. You need `git` and push rights to the repo.
**You do not need `oc`, cluster access, or admin help.**

### Step B1 — Clone and branch

```bash
git clone https://github.com/esarath/argo-CD-automate-repeted-task-OCP.git
cd argo-CD-automate-repeted-task-OCP
git checkout -b onboard-<your-team-name>
```

### Step B2 — Create your team config

```bash
mkdir -p teams/<your-team-name>
cp teams/_template/team-config.example.yaml teams/<your-team-name>/team-config.yaml
```

Edit `teams/<your-team-name>/team-config.yaml`. Minimum required edit:

```yaml
teamName: <your-team-name>          # MUST equal the folder name
quota:
  cpuRequests: "10"
  cpuLimits: "20"
  memoryRequests: 20Gi
  memoryLimits: 40Gi
```

Rules CI will enforce (fix them in the file, not in the cluster):
- `teamName` = folder name = lowercase DNS name (`a-z`, `0-9`, `-`), ≤63 chars
- never `openshift-*`, `kube-*`, `default`, `kubernetes`
- `networkPolicy.defaultDeny` must stay `true`
- put access as `adminGroups`/`developerGroups`/`viewerGroups` (AD/LDAP
  group names) — individual `admins`/`developers`/`viewers` also work

Optional pre-check locally (needs `python3` + `pyyaml`):

```bash
python3 scripts/validate_team_config.py     # exit 0 = good
```

### Step B3 — Push and open the PR

```bash
git add teams/<your-team-name>/
git commit -m "onboard team <your-team-name>"
git push -u origin onboard-<your-team-name>
```

Open a Pull Request to `main` on GitHub.

**What happens next (nothing for you to run):**
1. `Validate` workflow runs (~1–2 min) — if red, read the failed job log,
   fix the yaml, push again to the same branch.
2. Platform team reviews and merges.
3. ArgoCD detects the new folder (instant with webhook, else ≤3 min).
4. Your namespace + quota + limits + network policies + access are created.

### Step B4 — Confirm (optional; read-only)

```bash
oc get ns <your-team-name>                       # Active
oc get quota,limitrange,netpol -n <your-team-name>
```

or open the GitOps console and watch `<team>-onboarding` go **Synced /
Healthy**:
`https://openshift-gitops-server-openshift-gitops.apps.lab.ocp.local`
→ **LOG IN VIA OPENSHIFT**.

---

## Phase C — Day-2 operations

### Change a team's quota / access / policies

Edit the same `team-config.yaml` in a new PR → merge → ArgoCD updates
the live objects. Example: raise `quota.cpuLimits` from `"20"` to `"40"`.

### Offboard a team

```bash
git rm -r teams/<team-name>
git commit -m "offboard team <team-name>" && git push
# open PR -> merge
```

ArgoCD `prune` deletes the namespace and everything inside it.
**Data/workloads inside the namespace are destroyed — confirm with the
team before merging.**

### Preview what a config will create (no cluster needed)

```bash
helm template <team> charts/team-onboarding -f teams/<team>/team-config.yaml \
  --set teamName=<team>
```

---

## 8. Troubleshooting

| Symptom | Where to look | Likely cause / fix |
|---|---|---|
| `oc get pods -n openshift-gitops` shows nothing | `oc get csv -n openshift-operators` | Operator not finished installing; wait for `Succeeded` |
| Application stuck `OutOfSync`, events say `namespaces is forbidden` | `oc describe application <x>-onboarding -n openshift-gitops` | Step A3 skipped — apply `01-argocd-cluster-rbac.yaml` |
| App exists but `ComparisonError`/`resource not permitted` | AppProject in ArgoCD UI | Kind not whitelisted — only the chart's 6 kinds are allowed by design |
| CI job `validate-team-configs` red | Failed job log | Read the `FAIL:` lines — each names the file and the rule |
| Folder created but no Application after ~5 min | `oc get applicationset team-onboarding -n openshift-gitops -o yaml` → `.status` | File must be named exactly `team-config.yaml` under `teams/<dir>/` |
| App `Synced` but namespace missing | `helm template ...` locally | `teamName` != folder name, or a chart `fail` guard triggered (reserved name) |
| Quota edit merged but cluster unchanged | `argocd app get <team>-onboarding` → `Health` | App suspended or OutOfSync — check UI; `argocd app sync <team>-onboarding` |
| Manual `oc` change to a team namespace got reverted | — | Working as designed (`selfHeal`). Change it via PR to the config instead |

## Where each command runs — cheat sheet

| Command pattern | Runs on | Who |
|---|---|---|
| `oc apply -f bootstrap/...`, `oc get applications` | Admin workstation logged into the cluster | Platform admin (Phase A only) |
| `git clone/push`, `cp`, edit `team-config.yaml` | Any developer workstation | Developer |
| `python3 scripts/validate_team_config.py` | Same, optional local check | Developer |
| `helm template ...` (preview) | Any workstation with helm | Either |
| PR, merge, webhook settings | github.com UI | Developer opens; platform approves |
| ArgoCD UI | Browser — `openshift-gitops-server-openshift-gitops.apps.lab.ocp.local` | Either |
