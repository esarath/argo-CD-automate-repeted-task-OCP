# 06 — Self-Service Onboarding: team-config.yaml reference

The only file a developer ever writes. Everything else is generated.

## Minimal example

```yaml
teamName: payments
quota:
  cpuRequests: "10"
  cpuLimits: "20"
  memoryRequests: 20Gi
  memoryLimits: 40Gi
```

## Full field reference

| Field | Type | Default | Notes |
|---|---|---|---|
| `teamName` | string | **required** | DNS-1123; must match folder name; becomes the namespace |
| `displayName` | string | `teamName` | OpenShift console label |
| `admins` / `adminGroups` | list | `[]` | `admin` ClusterRole in the ns (member mgmt) |
| `developers` / `developerGroups` | list | `[]` | `edit` — deploy workloads |
| `viewers` / `viewerGroups` | list | `[]` | `view` — read-only |
| `quota.cpuRequests` | qty | `"4"` | namespace-wide sum of pod CPU requests |
| `quota.cpuLimits` | qty | `"8"` | namespace-wide sum of CPU limits |
| `quota.memoryRequests` | qty | `8Gi` | |
| `quota.memoryLimits` | qty | `16Gi` | |
| `quota.pods` | qty | `"50"` | object-count cap |
| `quota.services` | qty | `"20"` | |
| `quota.storageRequests` | qty | `100Gi` | sum of PVC requests |
| `limits.defaultCpuRequest` | qty | `100m` | pod default when unset |
| `limits.defaultCpuLimit` | qty | `500m` | also the per-container **max** |
| `limits.defaultMemoryRequest` | qty | `256Mi` | |
| `limits.defaultMemoryLimit` | qty | `1Gi` | also the per-container max |
| `networkPolicy.*` | bool | all `true` | `defaultDeny` may not be `false` (CI policy) |
| `serviceAccount.enabled` | bool | `false` | creates `<team>-deployer` |
| `serviceAccount.name` | string | `<team>-deployer` | |
| `serviceAccount.withEditRole` | bool | `false` | grants `edit` to the SA (CI deploys) |

## Contract rules (enforced in CI)

1. `teamName` matches `teams/<folder>` and is not a reserved name
   (`openshift-*`, `kube-*`, `default`, `kubernetes`).
2. Unknown keys are rejected — typos can't silently no-op.
3. `networkPolicy.defaultDeny: false` is rejected — isolation is
   platform policy, not a team choice.
4. Per-container limit ceiling must fit inside the namespace quota.
5. All quantity strings must parse as Kubernetes quantities.

## What gets created for `teamName: payments`

| Object | Name |
|---|---|
| Namespace | `payments` |
| ResourceQuota | `payments-quota` |
| LimitRange | `payments-limits` |
| NetworkPolicy | `default-deny-all`, `allow-same-namespace`, `allow-from-openshift-ingress`, `allow-from-openshift-monitoring`, `allow-dns-egress` |
| RoleBinding | `team-admin`, `team-edit`, `team-view` (per populated lists) |
| ServiceAccount (+RoleBinding `deployer-edit`) | `payments-deployer` (if enabled) |

## Offboarding

`git rm -r teams/payments && git push` → the ApplicationSet drops the
Application, `prune: true` deletes the namespace and everything in it.
Same review trail as onboarding.
