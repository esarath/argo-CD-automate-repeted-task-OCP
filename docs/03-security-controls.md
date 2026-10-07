# 03 — Security Controls

Every team namespace is born with this posture — no team can opt out
silently (CI validator rejects `defaultDeny: false`; AppProject bounds
what can be created at all).

## 1. Network isolation (NetworkPolicy bundle)

| Policy | Effect |
|---|---|
| `default-deny-all` | Ingress+egress denied for every pod — zero trust baseline |
| `allow-same-namespace` | Team's pods talk to each other (intra-app traffic) |
| `allow-from-openshift-ingress` | Routes work — router namespace can reach pods |
| `allow-from-openshift-monitoring` | Prometheus can scrape `/metrics` |
| `allow-dns-egress` | UDP/TCP 53 + UDP 5353 to openshift-dns only |

Consequence: a compromised pod in `payments` cannot reach pods in
`analytics`, cannot reach the cluster datastore, cannot exfiltrate except
via DNS. Cross-team traffic requires an explicit PR adding a policy —
visible, reviewable, auditable.

## 2. Resource governance

| Object | Purpose |
|---|---|
| ResourceQuota | Namespace aggregate ceilings — one team cannot starve the cluster |
| LimitRange | Per-container defaults + ceiling — a pod without requests can't bypass the quota, and can't exceed the container max |
| `count/resourcequotas: 1` | Teams cannot stack additional quota objects |

## 3. Access control (RBAC)

* Least privilege by default: team members get `admin`/`edit`/`view`
  **inside their namespace only** (RoleBinding, not ClusterRole).
* Prefer `*Groups` lists (LDAP/AD-synced) over individual users — joiners/
  leavers handled in the IdP, not in git.
* Optional `<team>-deployer` ServiceAccount with `automountServiceAccountToken:
  false`; `withEditRole` grants deploy rights for CI — nothing more.
* `Secret` is blacklisted at the AppProject level: onboarding never writes
  credentials (secrets belong in External Secrets / Vault anyway).

## 4. Platform-layer guardrails

| Layer | Guardrail |
|---|---|
| Chart | `teamName` DNS-1123 + reserved-name rejection (`openshift-*`, `kube-*`, `default`…) evaluated at **render time** — fails the pipeline, never reaches the API |
| CI | `validate_team_config.py`: unknown keys, reserved names, quota parse, container-limit ≤ quota sanity, `defaultDeny` cannot be false |
| AppProject | source/repo/kind/destination whitelists + Secret blacklist |
| ArgoCD | `selfHeal` reverts out-of-band edits; `prune` removes orphaned resources |

## Production considerations

* **SCC/PSA**: namespace gets the default `restricted` SCC automatically —
  teams cannot run privileged pods or hostNetwork/hostPath without a
  separate, platform-controlled grant. Keep it that way.
* **Egress**: DNS-only egress is the floor; teams needing external egress
  should add explicit policies (egress firewall/EgressIP at cluster level
  if required by compliance).
* **Image provenance**: pair with ImagePolicy/kyverno for allowed
  registries — out of scope of the namespace contract itself.
* **Audit**: every change = a git commit (author, approver, timestamp) +
  ArgoCD sync history + OCP API audit log. Three correlated trails.
