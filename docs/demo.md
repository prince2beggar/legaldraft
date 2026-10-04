# AIN-AI — Sprint S0 Demo Script (Clean Machine Verification)

This document provides a clean-machine step-by-step verification guide for **Sprint S0 — Scaffold** of the AIN-AI Bangladesh Legal-Tech Platform per SRS v2.0.

---

## 1. Single Port Specification

> **Official Unified Port:** **`8088`**
>
> All web interfaces, admin views, and API endpoints run consistently on port **`8088`** locally and in container configurations.

| Surface | URL | Description |
|---|---|---|
| **Citizen & Advocate Web App** | `http://localhost:8088/` | Default Bengali (`lang="bn"`), Noto Sans Bengali typography |
| **English Shell** | `http://localhost:8088/?lang=en` | English locale (`lang="en"`) |
| **Admin Portal** | `http://localhost:8088/admin` | Verification queue, audit trail, knowledge base |
| **Liveness Health Endpoint** | `http://localhost:8088/health` | Fast JSON health ping |
| **Readiness Health Endpoint** | `http://localhost:8088/health/ready` | Database & dependency connectivity check |
| **Feature Flags Matrix** | `http://localhost:8088/health/flags` | M01–M11 enabled, M12–M25 disabled |

---

## 2. Prerequisites & Environment Setup

### On a Clean Machine:
1. **Python 3.11+** installed.
2. Clone repository:
   ```bash
   git clone https://github.com/mdprince007/bangladesh-legal-tech.git
   cd bangladesh-legal-tech
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
4. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   pip install ruff mypy pytest beautifulsoup4 alembic
   ```

---

## 3. Step-by-Step Demo Execution

### Step 1: Run the Automated CI Pipeline (One Command)
Run the automated CI pipeline locally to verify linting, static type safety, reversible database migrations, and accessibility in one step:

```bash
python run_ci.py
```

**Expected Output:**
```text
*****************************************************************
  AIN-AI Local CI Pipeline — Sprint S0 Definition of Done
*****************************************************************

=================================================================
 CI STAGE: 1. Code Linting (Ruff)
 Command:  python -m ruff check .
=================================================================
All checks passed!
[PASSED] Stage '1. Code Linting (Ruff)'

=================================================================
 CI STAGE: 2. Static Type Checking (Mypy)
 Command:  python -m mypy packages services --explicit-package-bases --ignore-missing-imports
=================================================================
Success: no issues found in 13 source files
[PASSED] Stage '2. Static Type Checking (Mypy)'

=================================================================
 CI STAGE: 3. Automated Tests & Reversible Migrations (Pytest)
 Command:  python -m pytest tests/s0 -v --tb=short
=================================================================
tests/s0/test_audit_chain_ac_s0_3.py::test_audit_hash_chain PASSED
tests/s0/test_audit_chain_ac_s0_3.py::test_audit_tamper_detection PASSED
tests/s0/test_e2e_smoke_and_a11y.py::test_home_page_renders_in_bn PASSED
tests/s0/test_e2e_smoke_and_a11y.py::test_home_page_renders_in_en PASSED
tests/s0/test_e2e_smoke_and_a11y.py::test_a11y_axe_shell_audit PASSED
tests/s0/test_e2e_smoke_and_a11y.py::test_design_token_contrast_compliance PASSED
tests/s0/test_feature_flags_ac_s0_5.py::test_phase1_mvp_flags_enabled_by_default PASSED
tests/s0/test_feature_flags_ac_s0_5.py::test_later_phase_modules_disabled PASSED
tests/s0/test_feature_flags_ac_s0_5.py::test_flag_override PASSED
tests/s0/test_health_ac_s0_1.py::test_liveness_endpoint PASSED
tests/s0/test_health_ac_s0_1.py::test_readiness_endpoint PASSED
tests/s0/test_health_ac_s0_1.py::test_feature_flags_endpoint PASSED
tests/s0/test_i18n_ac_s0_2.py::test_default_locale_is_bangla PASSED
tests/s0/test_i18n_ac_s0_2.py::test_english_translation PASSED
tests/s0/test_i18n_ac_s0_2.py::test_parameter_substitution PASSED
tests/s0/test_i18n_ac_s0_2.py::test_core_microcopy_keys_present PASSED
tests/s0/test_logging_ac_s0_4.py::test_redact_phone_numbers PASSED
tests/s0/test_logging_ac_s0_4.py::test_redact_emails PASSED
tests/s0/test_logging_ac_s0_4.py::test_redact_nids PASSED
tests/s0/test_logging_ac_s0_4.py::test_redact_dictionary_keys PASSED
tests/s0/test_reversible_migrations.py::test_migration_reversible_lifecycle PASSED
======================= 21 passed in 3.44s =======================
[PASSED] Stage '3. Automated Tests & Reversible Migrations (Pytest)'

*****************************************************************
[SUCCESS] ALL CI CHECKS PASSED! S0 DOD FULLY SATISFIED.
*****************************************************************
```

---

### Step 2: Start the Live Application
Launch the unified server on port **`8088`**:

```bash
python -m uvicorn services.api.app.main:app --host 0.0.0.0 --port 8088
```

---

### Step 3: Verify Interactive Surfaces

1. **Verify Home Shell (Bengali):**
   - Open browser at `http://localhost:8088/`
   - Verify: Document lang is `bn`, title contains `আইন-AI`, typography is `Noto Sans Bengali` / `Hind Siliguri`.
   - Verify tabs: Problem Advisory, Intake Chat, Drafting Studio, Risk & Health.

2. **Verify English Locale Shell:**
   - Open browser at `http://localhost:8088/?lang=en`
   - Verify: Document lang is `en`, title shows English localization.

3. **Verify Admin Portal:**
   - Open browser at `http://localhost:8088/admin`
   - Verify: Admin header, source audit queue, and tamper inspection views.

4. **Verify Health & Safety Guardrails:**
   ```bash
   curl http://localhost:8088/health
   curl http://localhost:8088/health/flags
   ```

---

### Step 4: Docker Compose Orchestration (Where Docker is Available)

On machines with Docker Desktop installed:
```bash
docker compose up -d
docker compose ps
```
The stack will spin up `postgres`, `redis`, `minio`, `api`, `worker`, and `web`. Access the live app at `http://localhost:8088/`.
