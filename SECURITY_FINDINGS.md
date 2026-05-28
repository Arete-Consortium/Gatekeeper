# Security Findings — Gatekeeper

**Sweep date:** 2026-05-28
**Tools:** semgrep (auto) · bandit · gitleaks · pip-audit
**Triage model:** claude-opus-4-7 (manual)
**Posture before sweep:** **MEDIUM** (existing CI: bandit + semgrep + Trivy fs/IaC + secret-scan; gaps in shell-injection coverage and a CDN-style false positive)
**Posture after sweep:** **LOW** (3 real findings closed, 2 documented FPs, 5 deferred k8s hardening notes)

---

## Summary

| Severity | Open | Fixed this sweep | False positives |
|---|---|---|---|
| HIGH | 0 | 2 (shell-injection) | 1 (insecure-websocket on dev scheme transform) |
| MEDIUM | 0 | 0 | 1 (B608 SQL — placeholders are `?` params) |
| LOW / WARNING | 5 (k8s securityContext) | 0 | 0 |
| INFO | 9 (mostly JS format strings) | 0 | 0 |

Compared to the prior fleet (BG/Herald/QM), Gatekeeper's CI is already mature (Bandit + Semgrep + Trivy fs + Trivy IaC + secret-scan all wired). The local sweep surfaced findings the existing CI either missed or hadn't yet caught at HIGH level.

---

## Fixed in this sweep

### 1. Workflow shell-injection (2 instances, semgrep ERROR)
Same `${{ github.* }}` interpolation pattern that BG had — patched via env vars + `jq -nc` JSON construction.

| File | Line | Vector |
|---|---|---|
| `.github/workflows/ci.yml` | 141 | Discord notify with `${{ github.repository }}`, `${{ github.ref_name }}`, `${{ job.status }}` |
| `.github/workflows/deploy.yml` | 76 | Same pattern |

### 2. Bandit B608 suppression (`pathfinding.py:369`)
The line already had `# nosemgrep` for the same finding from semgrep's sqlalchemy rule. Bandit uses its own suppression syntax — added `# nosec B608` inline. Underlying construction is safe: `placeholders = ",".join("?" * len(avoid_regions))` builds a count-derived literal; the actual `avoid_regions` values are passed as bound `?` parameters.

---

## Open — needs your call

### M1. k8s SecurityContext missing (4 findings: 2× postgres, 2× redis)
`k8s/postgres.yaml` and `k8s/redis.yaml` lack `securityContext` on the container spec:
- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`

**Not auto-patched because:** Per `CLAUDE.md`, Gatekeeper deploys on Fly.io — these k8s manifests appear to be reference / aspirational. Patching them safely requires understanding `postgres:15-alpine` init order (initdb runs as root before dropping to postgres user) and `redis:7-alpine` user expectations. If you do plan to deploy on k8s, the minimal-impact addition is:

```yaml
spec:
  containers:
    - name: postgres
      image: postgres:15-alpine
      securityContext:
        runAsNonRoot: false  # postgres image requires root for initdb
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
          add: [SETUID, SETGID]  # required for initdb's user-drop
```

For redis (no init-as-root requirement):
```yaml
        - name: redis
          securityContext:
            runAsNonRoot: true
            runAsUser: 999  # redis-alpine user
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
```

### L1. apps/mobile unsafe-formatstring (7 INFO)
JS template-literal patterns in `CacheService.ts`, `GatekeeperAPI.ts`, `ZKillboardService.ts`. INFO-level — review when next touching those files. Likely safe (template literals concatenating known-typed values), but worth confirming if any of them flow user input into a `RegExp` constructor or eval-shaped callsite.

### L2. cookies.ts non-literal-regexp (1 WARNING)
`apps/web/src/lib/cookies.ts:17` — `new RegExp(\`(?:^|; )${name}=([^;]*)\`)`. The `name` parameter is currently only called with the constant `CONSENT_KEY = 'gk_consent'`, so no current injection vector. If `parseCookie()` is ever called with user input, this becomes ReDoS-vulnerable. Defensive fix: escape `name` via a regex-escape helper.

---

## False positives (validated, not patched)

| Finding | Location | Why |
|---|---|---|
| `insecure-websocket` (semgrep ERROR) | `apps/web/src/components/map/useKillStream.ts:251` | Code at lines 249-251 does the correct scheme transform: `https://`→`wss://` then `http://`→`ws://`. The semgrep rule fires on the second `replace` (the dev-time `http://`→`ws://`) — but in production, `baseUrl` is always `https://` so the first replace runs and the second is a no-op. Safe by construction. |
| `B608 hardcoded_sql_expressions` (bandit) | `pathfinding.py:369` | Suppressed with `# nosec B608` this sweep. Placeholders are count-derived, values bound as params. |

---

## Verification

```bash
# Re-run sweep
semgrep --config=auto --json --quiet \
  --exclude=node_modules --exclude=.venv --exclude=.next --exclude=htmlcov \
  --exclude=.pytest_cache --exclude=.ruff_cache --exclude=helm \
  -o /tmp/gk-semgrep.json .

bandit -r backend streamlit -f json -q -x backend/.venv,.venv
gitleaks detect --no-banner
pip-audit -r backend/requirements.txt
```

Existing CI (`.github/workflows/sast.yml`) covers: Bandit (HIGH+), Semgrep (auto + p/security-audit + p/python), Trivy fs (CRITICAL), Trivy IaC. Adequate ongoing gate — no new workflow needed.
