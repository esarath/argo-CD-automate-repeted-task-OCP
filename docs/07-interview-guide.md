# 07 — Interview / Review talking points

## Why this reduces toil

* Manual onboarding was 3+ kubectl commands × N objects × per-request
  queueing — now it's "merge a PR". Toil is eliminated, not just faster:
  there is **no ops action at all** in the happy path.
* Offboarding, quota changes, policy updates ride the same pipeline —
  no separate runbooks to keep in sync.
* The ApplicationSet removes the meta-toil too: nobody creates or
  babysits ArgoCD Applications by hand.

## Why GitOps beats manual kubectl

| Property | Manual kubectl | GitOps |
|---|---|---|
| Source of truth | Cluster (drifts silently) | Git (immutable history) |
| Consistency | Per-operator variance | One chart — identical output every time |
| Review | None (commands are invisible) | PR + CI + CODEOWNERS |
| Rollback | Reconstruct by hand | `git revert` — the cluster follows |
| Audit | API audit log only | commit ↔ PR ↔ sync ↔ API chain |
| Recovery | Rebuild from memory | Re-point ArgoCD at git — self-heals |

## Operational savings

* Request→provision latency: ticket SLA (hours–days) → merge+sync (~minutes).
* Senior-engineer time freed from namespace plumbing for architecture work.
* Fewer snowflake namespaces → fewer "works in team-A but not team-B"
  incidents and faster incident isolation.

## Security improvements

* Zero-trust network baseline is **on by construction** — teams can't
  forget it because they never write it.
* AppProject whitelists bound the blast radius of even a merged mistake.
* Separation of duties: proposer (dev), approver (platform), applier
  (ArgoCD) are three different identities.
* Secrets never flow through the onboarding path (blacklisted kind).

## Auditability improvements

* Every namespace is traceable to an approved PR — "who created this and
  why" is a git log query, not an archaeology dig.
* Compliance evidence is generated as a side effect: the CI validator
  log, the AppProject policy, and ArgoCD sync history.

## SRE / Platform Engineering benefits

* **Error budgets**: self-service removes a toil source that scales
  linearly with org growth.
* **Fleet-wide change propagation**: new baseline policy = one chart PR —
  rolls out uniformly; that is the "cattle not pets" argument at the
  namespace level.
* **Paved road**: teams get a secure, monitored, quota'd namespace
  without learning the controls — adoption *is* the compliance path.
* **Platform as product**: `team-config.yaml` is the API contract; the
  implementation can evolve (Kustomize→Helm→crossplane) without
  changing the developer experience.

## One-liner for interviews

> "We turned namespace provisioning from a ticket-driven manual runbook
> into a declarative contract — teams describe what they need in git,
> an ApplicationSet + Helm chart renders the guardrails, and ArgoCD
> enforces git as the source of truth with self-heal and prune."
