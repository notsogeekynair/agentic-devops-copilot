# Technical Specification — {{title}}

## 1. Summary
{{summary}}

## 2. Business Context & Goals
- Primary objective: {{primary_objective}}
- Success metrics:
  - {{metric_1}}
  - {{metric_2}}

## 3. Scope
**In-scope**
- {{in_scope_1}}
- {{in_scope_2}}

**Out-of-scope**
- {{out_scope_1}}

## 4. Functional Requirements
- {{functional_1}}
- {{functional_2}}

## 5. APIs (see OpenAPI file)
- Base path: {{base_path}}
- Services: {{services}}

## 6. Data Model
- Entities:
  - {{entity_1}}: fields: {{fields_1}}
  - {{entity_2}}: fields: {{fields_2}}

## 7. Non-Functional Requirements
- Performance: {{nfr_perf}}
- Security: {{nfr_sec}}
- Reliability: {{nfr_rel}}
- Observability: {{nfr_obs}}

## 8. Acceptance Criteria
- {{ac_1}}
- {{ac_2}}

## 9. Test Plan
- Unit tests:
- Integration tests:
- Smoke tests:

## 10. Deployment & Ops
- Runtime: {{runtime}}
- IaC strategy: CDK/Terraform
- CI/CD: CodeBuild / CodePipeline (generated)
- Environments: dev → qa → prod
``