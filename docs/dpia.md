# AIN-AI — Data Protection Impact Assessment (DPIA)

**Jurisdiction:** Bangladesh (aligned with Personal Data Protection principles)  
**Scope:** Phase 1 MVP  

---

## 1. Principles of Data Processing
1. **Lawfulness, Fairness and Transparency:** Explicit consent obtained at onboarding; plain-language privacy notice in Bangla; zero deceptive UI patterns.
2. **Purpose Limitation:** User legal documents and case facts are processed strictly to explain, draft, and manage the user's specific case. Data is NEVER used to train generic AI models (HR-12).
3. **Data Minimization:** Only fields necessary for the selected legal task are extracted. Identity papers (NID, passports) are treated as opaque binary storage in Phase 1 without unnecessary field extraction.
4. **Accuracy:** Automated OCR/HTR outputs start in `extracted` state. Only user-confirmed (`reviewed`) or officially verified (`verified`) fields flow into legal drafts and deadlines.
5. **Storage Limitation:** Soft-delete retention window of 30 days before permanent cryptographic shredding, unless active legal hold applies.
6. **Integrity and Confidentiality:** Encrypted at rest using AES-256; encrypted in transit using TLS 1.3.

---

## 2. User Rights & Controls
- **Right to Access & Portability:** Single-click async export of all user-owned cases, documents, drafts, and audit trails (`POST /me/export`).
- **Right to Erasure:** User-initiated account and document deletion (`POST /me/delete`).
- **Granular Consent & Immediate Revocation:** Sharing a case with a lawyer or third party requires a time-bounded, explicit consent grant with revocation taking effect in ≤60 seconds.
