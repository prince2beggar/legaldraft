# Service Level Objectives (SLOs) & Error Budgets

This document defines the production availability and latency Service Level Objectives (SLOs), error budgets, and response procedures for AIN-AI (আইন-AI) across all core modules.

## 1. Service Level Objectives (SLOs)

| Service Area | Metric | Target | Measurement Window | Alert Threshold |
|---|---|---|---|---|
| **API Availability** | Successful HTTP Requests (non-5xx) | **99.9%** | Rolling 30 Days | Downtime > 43.8 minutes / month |
| **Citizen Read Latency** | p95 Latency on Read Endpoints (`/home`, `/cases`, `/drafts`, `/health`) | **< 500 ms** | 5-minute rolling window | p95 > 500 ms for > 3 minutes |
| **Sharing & Recipient View** | p95 Latency on `/s/:token` | **< 400 ms** | 5-minute rolling window | p95 > 400 ms for > 2 minutes |
| **Slow-3G First Useful Screen** | Client First Contentful Paint (FCP) on throttled Slow-3G | **<= 4.0 s** | Synthetic Browser Audit | FCP > 4.0 s |
| **Audit Log Integrity** | Unbroken SHA-256 Hash Chain verification | **100% (Zero Divergence)** | Continuous Background Audit | Any hash mismatch triggers immediate P0 alert |
| **AI Triage Response** | FakeLLM fallback latency / LLM Gateway response | **< 2.5 s** | Rolling 1 hour | p95 > 3.0 s |

## 2. Error Budget Allocation & Burn Rate

- **Monthly Availability Error Budget (99.9%)**: 0.10% permissible failure rate (~43.2 minutes of total downtime per month).
- **Burn Rate Rules**:
  - **1x Burn Rate**: Normal consumption (budget lasts 30 days).
  - **2x - 5x Burn Rate**: Minor service degradation. Automated ticket generated; investigation within 2 hours.
  - **> 14.4x Burn Rate** (2% budget consumed in 1 hour): P1 Alert dispatched; active engineering intervention.
  - **Budget Exhaustion**: Freeze feature deployments; focus sprint resources exclusively on stability, reliability, and bug fixes.

## 3. High Concurrency Bottleneck Analysis

- **SQLite In-Memory / File-Based Deployment**:
  - Benchmarks confirm read latencies p95 < 40 ms on single-process instances.
  - Write concurrency under SQLite is bottlenecked by single-writer file locking.
  - Simulation of 1,000 concurrent writes requires production Postgres migration with connection pooling (e.g., PgBouncer).
- **Target Status**:
  - In-development SQLite verification: **TESTED & SATISFIED** for read/write under isolated test suites.
  - 1,000 Concurrent User Production Postgres Target: **UNVERIFIED** (Pending managed PostgreSQL cluster configuration in production staging).
