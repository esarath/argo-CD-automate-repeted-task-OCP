#!/usr/bin/env python3
"""Validate every teams/*/team-config.yaml against policy.

Runs in CI (.github/workflows/validate.yaml) and locally:

    python3 scripts/validate_team_config.py

Checks (beyond YAML/schema):
  * teamName is a DNS-1123 label and matches the folder name
  * no reserved/system namespace names
  * quotas are present and parse as quantities
  * limits <= quota sanity (cpu limits <= quota limits)
  * only known keys are used
Exit 1 on any violation.
"""
import glob
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: pip install pyyaml")

ALLOWED_KEYS = {
    "teamName", "displayName", "admins", "adminGroups", "developers",
    "developerGroups", "viewers", "viewerGroups", "quota", "limits",
    "networkPolicy", "serviceAccount",
}
QUOTA_KEYS = {
    "cpuRequests", "cpuLimits", "memoryRequests", "memoryLimits",
    "pods", "services", "storageRequests",
}
LIMITS_KEYS = {
    "defaultCpuRequest", "defaultCpuLimit",
    "defaultMemoryRequest", "defaultMemoryLimit",
}
NP_KEYS = {
    "defaultDeny", "allowSameNamespace", "allowFromIngress",
    "allowFromMonitoring", "allowDNS",
}
SA_KEYS = {"enabled", "name", "withEditRole"}
RESERVED_PREFIXES = ("openshift-", "kube-", "default", "kubernetes")
DNS1123 = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
QUANTITY = re.compile(r"^\d+(\.\d+)?([EPTGMK]i?|[num])?$")

errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


def cpu(v):
    """cpu quantity -> millicores for comparison."""
    v = str(v)
    return int(float(v[:-1])) if v.endswith("m") else int(float(v) * 1000)


def mem(v):
    """memory quantity -> bytes (approx, Gi/Mi only for simplicity)."""
    v = str(v)
    mult = {"Gi": 1 << 30, "Mi": 1 << 20, "Ki": 1 << 10, "G": 10**9,
            "M": 10**6, "K": 10**3}
    for suffix, m in mult.items():
        if v.endswith(suffix):
            return int(float(v[: -len(suffix)]) * m)
    return int(float(v))


files = sorted(glob.glob("teams/*/team-config.yaml"))
if not files:
    errors.append("no teams/*/team-config.yaml files found")

for path in files:
    folder = path.split("/")[1]
    ctx = f"{path}"
    try:
        cfg = yaml.safe_load(open(path))
    except Exception as e:  # noqa: BLE001
        errors.append(f"{ctx}: YAML parse error: {e}")
        continue
    if not isinstance(cfg, dict):
        errors.append(f"{ctx}: not a YAML mapping")
        continue

    check(not (set(cfg) - ALLOWED_KEYS),
          f"{ctx}: unknown keys {sorted(set(cfg) - ALLOWED_KEYS)}")

    name = cfg.get("teamName")
    check(bool(name), f"{ctx}: teamName missing")
    if name:
        check(bool(DNS1123.match(str(name))) and len(str(name)) <= 63,
              f"{ctx}: teamName '{name}' is not a DNS-1123 label")
        check(not str(name).startswith(RESERVED_PREFIXES),
              f"{ctx}: teamName '{name}' collides with a reserved namespace")
        check(folder == name,
              f"{ctx}: folder 'teams/{folder}' != teamName '{name}'")

    q = cfg.get("quota", {})
    check(bool(q), f"{ctx}: quota section required")
    check(not (set(q) - QUOTA_KEYS),
          f"{ctx}: unknown quota keys {sorted(set(q) - QUOTA_KEYS)}")
    for k, v in q.items():
        check(bool(QUANTITY.match(str(v))),
              f"{ctx}: quota.{k}='{v}' is not a k8s quantity")

    lim = cfg.get("limits", {})
    check(not (set(lim) - LIMITS_KEYS),
          f"{ctx}: unknown limits keys {sorted(set(lim) - LIMITS_KEYS)}")

    np_ = cfg.get("networkPolicy", {})
    check(not (set(np_) - NP_KEYS),
          f"{ctx}: unknown networkPolicy keys {sorted(set(np_) - NP_KEYS)}")
    if np_.get("defaultDeny") is False:
        errors.append(f"{ctx}: networkPolicy.defaultDeny=false is not "
                      "permitted by platform policy")

    sa = cfg.get("serviceAccount", {})
    check(not (set(sa) - SA_KEYS),
          f"{ctx}: unknown serviceAccount keys {sorted(set(sa) - SA_KEYS)}")

    # sanity: container ceiling must not exceed the namespace quota
    try:
        if lim.get("defaultCpuLimit") and q.get("cpuLimits"):
            check(cpu(lim["defaultCpuLimit"]) <= cpu(q["cpuLimits"]),
                  f"{ctx}: per-container cpu limit exceeds quota cpuLimits")
        if lim.get("defaultMemoryLimit") and q.get("memoryLimits"):
            check(mem(lim["defaultMemoryLimit"]) <= mem(q["memoryLimits"]),
                  f"{ctx}: per-container memory limit exceeds quota memoryLimits")
    except Exception as e:  # noqa: BLE001
        errors.append(f"{ctx}: quantity comparison failed: {e}")

for e in errors:
    print(f"FAIL: {e}")
if not errors:
    print(f"OK: {len(files)} team-config file(s) valid")
sys.exit(1 if errors else 0)
