import os
import json
import time
import yaml
import boto3
from datetime import datetime
from pathlib import Path

class SpecWriterAgent:
    """
    Turns a ticket into:
      - docs/specs/<ticket_id>-spec.md
      - docs/specs/<ticket_id>-openapi.yaml

    Strategy:
      - If BEDROCK configured -> use LLM to write high-quality spec
      - Else -> render from templates + heuristics (fallback)
    """

    def __init__(self, model_id=None, region=None):
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.docs_dir = Path("docs/specs")
        self.templates_dir = Path("docs/templates")
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self.bedrock = None
        if self.model_id:
            try:
                self.bedrock = boto3.client("bedrock-runtime", region_name=self.region)
            except Exception as e:
                print(f"[SpecWriter] Bedrock init failed: {e}. Will use fallback.")

    def run(self, input):
        """
        input = {
          "ticket": {
             "id": "TKT-123",
             "title": "...",
             "description": "...",
             "acceptance_criteria": ["...", "..."],
             "constraints": ["...", "..."]
          }
        }
        """
        ticket = input.get("ticket", {})
        ticket_id = ticket.get("id", f"TKT-{int(time.time())}")
        title = ticket.get("title", "Untitled Feature")

        spec_path = self.docs_dir / f"{ticket_id}-spec.md"
        openapi_path = self.docs_dir / f"{ticket_id}-openapi.yaml"

        if self.bedrock:
            try:
                spec_md, openapi_yaml = self._generate_with_bedrock(ticket)
            except Exception as e:
                print(f"[SpecWriter] Bedrock generation failed: {e}. Falling back.")
                spec_md, openapi_yaml = self._generate_with_fallback(ticket)
        else:
            spec_md, openapi_yaml = self._generate_with_fallback(ticket)

        spec_path.write_text(spec_md, encoding="utf-8")
        openapi_path.write_text(openapi_yaml, encoding="utf-8")

        return {
            "status": "ok",
            "ticket_id": ticket_id,
            "outputs": {
                "spec_md": str(spec_path),
                "openapi_yaml": str(openapi_path)
            }
        }

    # ---------- Bedrock path ----------
    def _generate_with_bedrock(self, ticket: dict):
        system_prompt = (
            "You are a senior software architect. Produce a precise, production-grade "
            "technical specification for the requested feature. Output MUST be clean "
            "Markdown suitable for review by architects, developers, and DevOps. "
            "Include functional/non-functional requirements, API overview, data model, "
            "acceptance criteria, test plan, deployment/IaC notes. Keep it concise and actionable."
        )

        user_prompt = self._compose_user_prompt(ticket)

        # Note: Some models use 'messages' (Claude 3.5) structure. Adjust if needed for your chosen model.
        payload = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ],
            "max_tokens": 3000,
            "temperature": 0.2
        }

        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )

        body = json.loads(response["body"].read())
        # Extract text depending on model schema
        spec_text = self._extract_text_from_body(body)

        # Ask for OpenAPI next (shorter, deterministic)
        openapi_prompt = self._compose_openapi_prompt(ticket)
        payload["messages"].append({"role": "user", "content": [{"type": "text", "text": openapi_prompt}]})
        payload["temperature"] = 0.0
        response2 = self.bedrock.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        body2 = json.loads(response2["body"].read())
        openapi_text = self._extract_text_from_body(body2)
        # Sanity: ensure YAML header exists
        if not str(openapi_text).strip().startswith("openapi:"):
            openapi_text = self._render_openapi_fallback(ticket)

        return spec_text, openapi_text

    def _extract_text_from_body(self, body):
        """
        Attempts to extract model text from Bedrock response (Claude-style).
        """
        # Claude 'messages' style:
        try:
            parts = body["output"]["message"]["content"]
            texts = []
            for p in parts:
                if p.get("type") == "text" and "text" in p:
                    texts.append(p["text"])
            return "\n".join(texts).strip()
        except Exception:
            pass

        # Fallback: try simple 'outputText'
        if "outputText" in body:
            return body["outputText"]

        return str(body)

    # ---------- Fallback path ----------
    def _generate_with_fallback(self, ticket: dict):
        title = ticket.get("title", "Untitled Feature")
        description = ticket.get("description", "")
        ac = ticket.get("acceptance_criteria", []) or []
        constraints = ticket.get("constraints", []) or []

        tmpl = (self.templates_dir / "spec_template.md").read_text(encoding="utf-8")
        spec_md = tmpl
        spec_md = spec_md.replace("{{title}}", title)
        spec_md = spec_md.replace("{{summary}}", description[:500] or "N/A")
        spec_md = spec_md.replace("{{primary_objective}}", "Automate ticket → spec → code → deploy")
        spec_md = spec_md.replace("{{metric_1}}", "Lead time reduction (%)")
        spec_md = spec_md.replace("{{metric_2}}", "Change failure rate (%)")
        spec_md = spec_md.replace("{{in_scope_1}}", "Spec generation from ticket")
        spec_md = spec_md.replace("{{in_scope_2}}", "OpenAPI draft")
        spec_md = spec_md.replace("{{out_scope_1}}", "Frontend UX")
        spec_md = spec_md.replace("{{functional_1}}", "Generate service scaffold and APIs")
        spec_md = spec_md.replace("{{functional_2}}", "Provide test plan & acceptance criteria")
        spec_md = spec_md.replace("{{base_path}}", "/api")
        spec_md = spec_md.replace("{{services}}", "alerts, health")
        spec_md = spec_md.replace("{{entity_1}}", "Alert")
        spec_md = spec_md.replace("{{fields_1}}", "id, type, severity, message, createdAt")
        spec_md = spec_md.replace("{{entity_2}}", "User")
        spec_md = spec_md.replace("{{fields_2}}", "id, email, preferences")
        spec_md = spec_md.replace("{{nfr_perf}}", "P95 < 200ms for read APIs")
        spec_md = spec_md.replace("{{nfr_sec}}", "IAM, JWT (Cognito), least-privilege")
        spec_md = spec_md.replace("{{nfr_rel}}", "99.9% availability, multi-AZ")
        spec_md = spec_md.replace("{{nfr_obs}}", "CloudWatch metrics/logs, traces")
        spec_md = spec_md.replace("{{ac_1}}", ac[0] if ac else "API responds with 200 for valid request")
        spec_md = spec_md.replace("{{ac_2}}", ac[1] if len(ac) > 1 else "Validation errors return 400 with details")
        spec_md = spec_md.replace("{{runtime}}", "AWS Lambda + API Gateway")

        openapi_yaml = self._render_openapi_fallback(ticket)
        return spec_md, openapi_yaml

    def _render_openapi_fallback(self, ticket: dict):
        title = ticket.get("title", "Service")
        base = (self.templates_dir / "openapi_skeleton.yaml").read_text(encoding="utf-8")
        return base.replace("{{title}}", title)

    # ---------- Prompt builders ----------
    def _compose_user_prompt(self, ticket: dict) -> str:
        title = ticket.get("title", "")
        description = ticket.get("description", "")
        ac = ticket.get("acceptance_criteria", []) or []
        constraints = ticket.get("constraints", []) or []

        return f"""
Create a production-ready technical specification for this ticket.

Title: {title}

Description:
{description}

Acceptance Criteria:
- {"\n- ".join(ac) if ac else "N/A"}

Constraints:
- {"\n- ".join(constraints) if constraints else "None"}

Include sections: Summary, Business Context & Goals, Scope (in/out), Functional Requirements,
APIs overview, Data Model, Non-Functional Requirements, Acceptance Criteria, Test Plan, Deployment & Ops (IaC/CI-CD).
Be concise and specific. Use bullet points where possible.
"""

    def _compose_openapi_prompt(self, ticket: dict) -> str:
        title = ticket.get("title", "Service")
        description = ticket.get("description", "")
        return f"""
Draft a minimal OpenAPI 3.0 YAML for the service '{title}' described below.
Include at least: /health and one example resource with CRUD (if applicable).
Keep it valid YAML starting with 'openapi: 3.0.3'. Only output YAML, no explanations.

Description:
{description}
"""

# Convenience entrypoint (optional)
def main():
    sample_ticket = {
        "id": "TKT-001",
        "title": "Customer Alerts microservice",
        "description": "As a platform, we need a microservice to create and fetch alerts for users.",
        "acceptance_criteria": [
            "Create alert: POST /alerts returns 201",
            "List alerts: GET /alerts?userId=... returns 200 and user alerts"
        ],
        "constraints": ["Latency P95 < 200ms for GET /alerts"]
    }
    agent = SpecWriterAgent()
    result = agent.run({"ticket": sample_ticket})
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
``