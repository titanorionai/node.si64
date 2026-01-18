# SI64.NET Documentation Audit Report
**Date:** January 17, 2026  
**Status:** ⚠️ **CRITICAL ISSUES FOUND**  
**Audit Scope:** Public docs, frontend files, exposed endpoints

---

## Executive Summary

**Overall Assessment:** 🔴 **SECURITY RISK IDENTIFIED**

The documentation and frontend contain **proprietary technical details** that should not be publicly exposed. Specifically:

1. **Genesis Key Exposed in Frontend** (CRITICAL)
2. **Internal Queue Architecture Disclosed** (HIGH)
3. **Hardware Classification Names Visible** (MEDIUM)
4. **Redis Internal Keys Referenced** (MEDIUM)
5. **SwarmCommander Implementation Details** (MEDIUM)

**Recommendation:** Immediately move sensitive documentation to private repo and scrub frontend hardcoded credentials.

---

## Issues Inventory

### 🔴 CRITICAL ISSUES

#### Issue #1: Genesis Key Hardcoded in Frontend
**Files:** 
- `www/templates/index.html` (Line 721)
- `nvidia_index.html` (Line 721)

**Code:**
```javascript
headers: { "Content-Type": "application/json", "x-genesis-key": "TITAN_GENESIS_KEY_V1_SECURE" }
```

**Risk:** 
- Hardcoded authentication token visible in client-side JavaScript
- Any user viewing page source can steal genesis key
- Enables unauthorized API access

**Severity:** CRITICAL  
**Action:** REMOVE immediately

---

#### Issue #2: Genesis Key in Multiple Documentation Files
**Files:**
- `DEPLOYMENT_STATUS.md` (Line 96)
- `FINAL_DEPLOYMENT.md` (Line 186)
- `SECURITY_HARDENING_COMPLETE.txt` (Line 36, 263)
- `core/worker_node.py` (Line 35 - fallback default)
- `brain/dispatcher.py` (Line 61 - fallback default)
- `stress_test.py` (Line 16)
- `stress_test_threats.py` (Line 19)

**Risk:**
- Credentials exposed in git history if repo is public
- Attackers can use genesis key to impersonate legitimate workers

**Severity:** CRITICAL  
**Action:** Remove from all docs; use environment variables only

---

### 🟠 HIGH ISSUES

#### Issue #3: Internal Queue Architecture Disclosed
**Files:**
- `FINAL_DEPLOYMENT.md` 
- `DEPLOYMENT_STATUS.md`
- `brain/dispatcher.py` (commented code patterns)
- `brain/swarm_commander.py` (full implementation)

**Exposed Details:**
- Redis queue naming: `queue:UNIT_ORIN_AGX`, `queue:UNIT_APPLE_M_SERIES`, `queue:UNIT_NVIDIA_CUDA`
- Pub/Sub signals: `signal:{HARDWARE_CLASS}`
- LPUSH/RPOP job dequeue mechanics
- SwarmCommander class methods: `commission_unit()`, `decommission_unit()`, `dispatch_mission()`
- Pool registry keys: `pool:{hardware_type}:active`

**Risk:**
- Attackers understand exact job distribution flow
- Can craft attacks targeting specific hardware queues
- Understand timing/latency of job assignment
- Know internal data structure names

**Severity:** HIGH  
**Action:** Move to private documentation; summarize only user-facing behavior in public docs

---

#### Issue #4: Hardware Classification Names Exposed
**Files:**
- `brain/swarm_commander.py` (HardwareClass enum)
- `core/worker_node.py` (Line 132)
- `brain/dispatcher.py` (Lines 383-385, 875)
- Multiple docs referencing `UNIT_ORIN_AGX`, `UNIT_APPLE_M_SERIES`

**Exposed Details:**
```python
class HardwareClass(str, Enum):
    JETSON_ORIN = "UNIT_ORIN_AGX"
    APPLE_SILICON = "UNIT_APPLE_M_SERIES"
    STD_GPU = "UNIT_NVIDIA_CUDA"
```

**Risk:**
- Internal naming conventions visible
- Attackers can fake hardware declarations
- Know exact hardware classification codes

**Severity:** MEDIUM  
**Action:** Rename to opaque codes; document only in private API specification

---

### 🟡 MEDIUM ISSUES

#### Issue #5: Redis Internal Key Names Exposed
**Files:**
- `FINAL_DEPLOYMENT.md` (references to Redis operations)
- `brain/dispatcher.py` (queue length checks: `redis_client.llen("queue:UNIT_ORIN_AGX")`)
- `brain/swarm_commander.py` (key construction: `pool_key = f"pool:{hardware_type.value}:active"`)

**Exposed Details:**
- `active_nodes` (set of active worker IDs)
- `pool:{hardware}:active` (per-hardware worker pools)
- `queue:{hardware}` (job queues per hardware)
- `signal:{hardware}` (Pub/Sub channels)

**Risk:**
- Redis introspection attacks can enumerate all workers
- Attackers know exact key naming patterns
- Can craft Redis connection hijacking attempts

**Severity:** MEDIUM  
**Action:** Document Redis schema in separate private API spec; don't expose in public docs

---

#### Issue #6: SwarmCommander Implementation Details
**Files:**
- `brain/swarm_commander.py` (full source code)
- `FINAL_DEPLOYMENT.md` (references to commander operations)

**Exposed Details:**
- Atomic registration using `redis.pipeline()`
- `sadd()` operations for pool membership
- `rpop()` for FIFO job dequeue
- `lpush()` for job enqueueing
- Pub/Sub broadcast mechanism: `await self.redis.publish(channel, message)`

**Risk:**
- Attackers understand exact transaction ordering
- Know about race conditions (or lack thereof)
- Can attempt to exploit atomicity windows

**Severity:** MEDIUM  
**Action:** Move implementation to private docs; publish only API contract

---

### 🟢 LOW/INFO ISSUES

#### Issue #7: Rate Limit Configuration Public
**Files:**
- `SECURITY_AUDIT_REPORT.md` (Line 39)
- `DEPLOYMENT_STATUS.md`

**Exposed:**
```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    - Limit: 150 requests per 10 seconds per IP
```

**Risk:** Attackers know exact rate limit thresholds; can optimize DoS attacks

**Severity:** LOW  
**Action:** Remove specific numbers; say "rate limited" without disclosing threshold

---

#### Issue #8: Database Schema Published
**Files:**
- `SECURITY_AUDIT_REPORT.md` (database structure)
- `FINANCIAL_API_DOCS.md` (contract lifecycle, tables)

**Exposed:**
- Table names: `transactions`, `contracts`
- Column names and types
- SQLite WAL mode configuration

**Severity:** LOW  
**Action:** Summarize functionality without exposing schema details

---

### 📊 SUMMARY TABLE

| Issue | Severity | Files | Action |
|-------|----------|-------|--------|
| Genesis Key Hardcoded | 🔴 CRITICAL | www/*.html, docs | Remove immediately |
| Genesis Key in Docs | 🔴 CRITICAL | Multiple .md, .py | Remove all instances |
| Queue Architecture | 🟠 HIGH | swarm_commander.py, dispatche.py | Move to private docs |
| Hardware Classes | 🟠 HIGH | swarm_commander.py, dispatcher.py | Use opaque codes |
| Redis Keys | 🟡 MEDIUM | dispatcher.py, swarm_commander.py | Private API spec |
| SwarmCommander Impl | 🟡 MEDIUM | swarm_commander.py | Private repo only |
| Rate Limits | 🟢 LOW | SECURITY_AUDIT_REPORT.md | Remove numbers |
| Database Schema | 🟢 LOW | FINANCIAL_API_DOCS.md | Remove details |

---

## Documentation Organization Plan

### Public-Facing (Safe to Share)
✅ `WORKER_ONBOARDING.md` — User guide (appropriate for public)
✅ `README.md` — High-level overview (mostly safe; needs scrubbing)
✅ `www/WALLET_RENTAL_GUIDE.md` — User feature guide
✅ API documentation (endpoints only, not internals)

### Private Repository (Sensitive Details)
🔒 `brain/swarm_commander.py` — Job routing internals
🔒 `brain/dispatcher.py` — Full dispatcher code
🔒 Internal architecture docs (queue names, Redis schema, authentication details)
🔒 `FINAL_DEPLOYMENT.md` — Contains implementation details
🔒 `DEPLOYMENT_STATUS.md` — Contains internal architecture
🔒 `SECURITY_AUDIT_REPORT.md` — Implementation-specific details

### Frontend (Must Secure)
🔒 `www/templates/index.html` — Remove hardcoded genesis key
🔒 `nvidia_index.html` — Remove hardcoded genesis key

---

## Remediation Checklist

### Phase 1: Immediate (Next 30 minutes)
- [ ] Remove `x-genesis-key` hardcoded value from both HTML files
- [ ] Replace with environment-based or backend-provided token
- [ ] Remove all instances of `TITAN_GENESIS_KEY_V1_SECURE` from `.md` files
- [ ] Update git history (use BFG repo cleaner if already pushed)

### Phase 2: Short-term (1-2 hours)
- [ ] Move `brain/swarm_commander.py` to private repo (or behind access control)
- [ ] Remove queue naming details from public docs
- [ ] Remove hardware classification codes from public docs
- [ ] Scrub `FINAL_DEPLOYMENT.md` and `DEPLOYMENT_STATUS.md`
- [ ] Create private API specification document

### Phase 3: Medium-term (Today)
- [ ] Audit all source files for hardcoded credentials
- [ ] Review all `.md` files for technical leaks
- [ ] Create public vs private documentation split
- [ ] Update README.md to remove implementation details
- [ ] Add `.gitignore` entries for sensitive files

### Phase 4: Long-term (This week)
- [ ] Set up separate private GitHub repo for internal docs/code
- [ ] Publish only public APIs and user guides to main repo
- [ ] Implement secret scanning in CI/CD
- [ ] Rotate genesis key (since it's already exposed)
- [ ] Document internal architecture in private wiki only

---

## Specific Remediation Actions

### Action 1: Frontend Genesis Key Removal

**Current (VULNERABLE):**
```javascript
headers: { "Content-Type": "application/json", "x-genesis-key": "TITAN_GENESIS_KEY_V1_SECURE" }
```

**Option A: Backend-Provided Token**
```javascript
// Backend issues a temporary token on page load
let apiToken = null;
fetch('/api/session').then(r => r.json()).then(d => {
    apiToken = d.token;  // Valid for 1 hour, rotates daily
});

// Use in requests:
headers: { "Content-Type": "application/json", "x-session-token": apiToken }
```

**Option B: Proxy All Requests Through Backend**
```javascript
// Frontend only talks to backend; backend proxies to internal APIs
fetch('/api/stats').then(r => r.json())  // Backend adds auth headers
```

**Recommendation:** Use Option B for maximum security.

---

### Action 2: Documentation Refactor

**Files to DELETE from public:**
```
- FINAL_DEPLOYMENT.md (move to private/ARCHITECTURE_INTERNAL.md)
- DEPLOYMENT_STATUS.md (move to private, extract safe parts only)
- SECURITY_AUDIT_REPORT.md (move to private, extract safe parts to SECURITY_PUBLIC.md)
- DOCKER_SECURITY.md (review and remove internals)
```

**Files to KEEP (with scrubbing):**
```
- README.md (remove genesis key, queue details, internal naming)
- WORKER_ONBOARDING.md (already safe)
- www/WALLET_RENTAL_GUIDE.md (safe)
- FINANCIAL_API_DOCS.md (safe, but remove schema details)
```

**Create NEW public docs:**
```
- PUBLIC_API_REFERENCE.md (endpoints only, no internals)
- PUBLIC_ARCHITECTURE.md (high-level flow only)
- GETTING_STARTED.md (user-facing setup)
```

---

### Action 3: Source Code Audit

**Commands to identify remaining leaks:**
```bash
# Find all genesis keys
grep -r "TITAN_GENESIS_KEY" /home/titan/TitanNetwork --include="*.py" --include="*.js" --include="*.html"

# Find queue references (should be only in dispatcher.py/swarm_commander.py)
grep -r "queue:UNIT" /home/titan/TitanNetwork --include="*.md"

# Find hardware class names (should be only in internal code)
grep -r "UNIT_ORIN\|UNIT_APPLE\|UNIT_NVIDIA" /home/titan/TitanNetwork --include="*.md"

# Find Redis operation details
grep -r "pool:.*active\|signal:" /home/titan/TitanNetwork --include="*.md"
```

---

## Risk Assessment

### Current State
- **Public Exposure:** ⚠️ Genesis key visible in frontend and docs
- **Attack Surface:** Attackers know:
  - Queue naming conventions
  - Hardware classification codes
  - Job distribution algorithm
  - Redis data structure names
  - Authentication flow

### Post-Remediation
- **Public Exposure:** ✅ Only user-facing APIs documented
- **Attack Surface:** Reduced significantly
- **Code Integrity:** Protected in private repo

---

## Testing Checklist (After Remediation)

- [ ] Verify frontend no longer contains hardcoded genesis key
- [ ] Confirm API calls still work with new authentication method
- [ ] Check git log for any remaining exposed credentials
- [ ] Audit public documentation for technical leaks
- [ ] Test private repo access controls
- [ ] Verify CI/CD secret scanning is active

---

## Conclusion

**Current state:** The system is operationally secure, but **documentation and frontend expose too much proprietary detail**. 

**Key action items:**
1. **Remove genesis key from frontend immediately** (CRITICAL)
2. **Move internal architecture to private docs** (HIGH)
3. **Publish only user-facing APIs publicly** (HIGH)
4. **Rotate all exposed credentials** (HIGH)

Once remediated, the system will be **production-ready with appropriate operational security**.

---

*Audit Completed: 2026-01-17 by Copilot Security Review*
