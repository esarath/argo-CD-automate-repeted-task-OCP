# GitOps Team Onboarding — Self-Service Namespaces on OpenShift

**Platform:** lab.ocp.local (OCP 4.20.35) · OpenShift GitOps (ArgoCD) · Helm

Automates what platform admins used to do by hand for every team request:

```
kubectl create namespace <team>
kubectl apply -f quota.yaml
kubectl apply -f network-policy.yaml
```

becomes: **open a PR that adds `teams/<team>/team-config.yaml`. Merge. Done.**

## How it works

```
Developer ──PR──> GitHub ──CI──> validate ──merge──> ArgoCD ApplicationSet
                                                        │
                                              git files generator scans
                                              teams/*/team-config.yaml
                                                        │ per team
                                                        v
                                          Helm chart team-onboarding
                                                        │
                                                        v
                              Namespace + ResourceQuota + LimitRange
                              + NetworkPolicies + RoleBindings (+ SA)
```

* `teams/` — one folder per team; the **only** thing a developer touches.
* `charts/team-onboarding/` — single source of truth for what a "team
  namespace" means (quota, limits, isolation, access).
* `applicationsets/` — the ApplicationSet that turns each team folder into
  an ArgoCD Application automatically (git files generator).
* `bootstrap/` — one-time platform setup: operator subscription, ArgoCD
  cluster RBAC, AppProject tenancy boundary.
* `.github/workflows/` — PR validation (yamllint, schema, helm lint+render,
  kubeconform) and post-merge deploy notification.
* `scripts/validate_team_config.py` — policy checks on team configs.
* `docs/` — architecture, security model, enterprise design, interview guide.

## Onboard a team (developer self-service)

```bash
cp -r teams/_template teams/payments
# edit teams/payments/team-config.yaml — rename to your team values
git checkout -b onboard-payments && git add teams/payments
git commit -m "onboard team payments" && git push -u origin onboard-payments
# open PR -> CI validates -> merge -> ArgoCD creates everything
```

Minimum viable config:

```yaml
teamName: payments
quota: {cpuRequests: "10", cpuLimits: "20",
        memoryRequests: 20Gi, memoryLimits: 40Gi}
```

Everything else falls back to secure defaults (see
[`teams/_template/team-config.example.yaml`](teams/_template/team-config.example.yaml)).

## One-time platform bootstrap

```bash
oc apply -f bootstrap/00-gitops-operator-subscription.yaml   # operator
oc apply -f bootstrap/01-argocd-cluster-rbac.yaml            # ArgoCD rights
oc apply -f bootstrap/02-appproject-platform-teams.yaml      # tenancy boundary
oc apply -f applicationsets/team-onboarding-appset.yaml      # discovery engine
```

GitOps console: <https://openshift-gitops-server-openshift-gitops.apps.lab.ocp.local>
(log in **via OpenShift** — cluster-admins map to ArgoCD admin.)

## Docs

| Doc | Contents |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | Repo layout, component design, diagram |
| [docs/02-openshift-gitops-setup.md](docs/02-openshift-gitops-setup.md) | Operator install, RBAC, AppProject details |
| [docs/03-security-controls.md](docs/03-security-controls.md) | Zero-trust networking, RBAC, quotas, guardrails |
| [docs/04-cicd-flow.md](docs/04-cicd-flow.md) | PR → merge → sync, step by step |
| [docs/05-enterprise-design.md](docs/05-enterprise-design.md) | 100+ teams, multi-cluster, hub-and-spoke, DR, audit, compliance |
| [docs/06-self-service-onboarding.md](docs/06-self-service-onboarding.md) | team-config.yaml field reference |
| [docs/07-interview-guide.md](docs/07-interview-guide.md) | Toil/SRE/auditability talking points |
