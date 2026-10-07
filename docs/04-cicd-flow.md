# 04 — CI/CD Flow, Step by Step

## The full journey of one onboarding request

```
Developer                         Platform
─────────                         ────────
  │
  │  1. cp -r teams/_template teams/payments
  │     edit team-config.yaml
  │  2. git push + open PR
  v
              ┌──────────────────────────────┐
              │ GitHub Actions: validate.yaml │
              │  • yamllint                   │
              │  • team-config policy check   │  3. must all pass
              │  • helm lint + helm template  │
              │  • kubeconform schemas        │
              └──────────────┬───────────────┘
                             │ green
              ┌──────────────v───────────────┐
              │ Human review (CODEOWNERS →   │  4. approval
              │ platform team owns teams/)   │
              └──────────────┬───────────────┘
                             │ merge to main
              ┌──────────────v───────────────┐
              │ deploy.yaml: render check +  │  5. post-merge
              │ optional ArgoCD webhook ping │
              └──────────────┬───────────────┘
              ┌──────────────v───────────────┐
              │ ArgoCD ApplicationSet        │  6. git files generator
              │ discovers teams/payments/    │     (webhook → instant,
              │ team-config.yaml             │      else ≤ ~3 min poll)
              └──────────────┬───────────────┘
              ┌──────────────v───────────────┐
              │ Application payments-        │  7. render helm chart
              │ onboarding (platform-teams)  │     with team's values
              └──────────────┬───────────────┘
              ┌──────────────v───────────────┐
              │ OpenShift                    │  8. apply
              │ ns payments + quota + limits │
              │ + 5 NetPols + RBAC (+ SA)    │
              └──────────────┬───────────────┘
                             │
              App = Synced + Healthy ── team starts deploying workloads
```

## What each stage guarantees

| Stage | Guarantee |
|---|---|
| CI validate | Config parses, names legal, quotas sane, chart renders, manifests match k8s schemas — **before** anything touches the cluster |
| PR review | Human judgment on *policy* (is this quota fair? should this team exist?) — machines can't answer that |
| ApplicationSet | Every `teams/` entry gets identical treatment — no "I forgot the network policy" variance |
| selfHeal | Post-merge, if someone `oc edit`s the quota, ArgoCD reverts it — git is truth |
| prune | `git rm -r teams/payments` + merge = namespace and contents deleted — offboarding is the same flow backwards |

## Failure modes & behaviour

| Failure | Result |
|---|---|
| Bad YAML in team-config | CI fails → merge blocked → cluster untouched |
| Reserved namespace name | CI + chart `fail` → blocked twice |
| Valid file, quota conflicts (e.g. ns exists with different owner) | App goes Degraded, visible in ArgoCD UI; other teams unaffected |
| ArgoCD unreachable at merge | Reconciles on next poll; git stays the queue of intent |

## Operational commands

```bash
# watch onboarding happen
oc get applications -n openshift-gitops | grep onboarding
oc get all -n payments            # resources appear
oc get netpol,quota,limitrange,rolebinding -n payments

# force a sync / debug
argocd app get payments-onboarding
argocd app sync payments-onboarding
argocd appset list
```
