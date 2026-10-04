# AIN-AI — Legal & Operational Risk Register

| Risk ID | Description | Impact | Probability | Mitigation Strategy | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | Unauthorized Practice of Law (UPL) challenge | High | Medium | Persistent disclaimer label (`legal.disclaimer.short`), plain-language explanation framing, zero outcome prediction, no legal advice claims. | Legal Counsel / Lead |
| **RSK-02** | Miscalculated deadline causing missed court filing | Critical | Low | Hard rule HR-08: zero LLM deadline computation; pure-code rules engine with visible calculation steps; user confirmation required. | Rules Engine Lead |
| **RSK-03** | Hallucinated citation or non-existent statute | High | Low | Citation Verifier verifies 100% of claims against approved source registry before displaying to user; unverified claims flagged or blocked. | Trust Kernel Lead |
| **RSK-04** | Accidental unauthorized data sharing | High | Low | Explicit ConsentSheet with granular scope and expiry; zero automatic sharing; revocation effective in ≤60 seconds. | Security Lead |
| **RSK-05** | Poor OCR quality on degraded/blurry documents | Medium | High | Multi-stage image enhancement, field-level confidence scores, explicit "extracted" state warning, user-in-the-loop editing. | CV & OCR Lead |
