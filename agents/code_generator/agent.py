import os
import yaml
from pathlib import Path
from typing import Dict


LAMBDA_HANDLER_TEMPLATE = """\
import json
import os
from datetime import datetime

def health(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "ts": datetime.utcnow().isoformat()})
    }

def not_implemented(event, context):
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Not implemented"})
    }
"""

SERVERLESS_YAML_TEMPLATE = """\
service: {service_name}

provider:
  name: aws
  runtime: python3.11
  region: {region}
  stage: dev
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:PutItem
            - dynamodb:GetItem
            - dynamodb:Query
            - dynamodb:UpdateItem
          Resource: "*"

functions:
  health:
    handler: handler.health
    events:
      - http:
          path: {base_path}/health
          method: get
{dynamic_functions}
plugins:
  - serverless-python-requirements

package:
  patterns:
    - '!node_modules/**'
    - '!__pycache__/**'
"""

REQUIREMENTS_TXT = """\
boto3
"""

MAKEFILE = """\
.PHONY: setup test run deploy

setup:
\tpython -m venv .venv && . ./.venv/Scripts/activate || . ./.venv/bin/activate; pip install -r requirements.txt

test:
\tpython -m pytest -q

run:
\t# Local Lambda test (requires serverless or sam). For now, just a placeholder.
\tpython -c "print('Run via SAM/Serverless or integrate FastAPI for local dev')"

deploy:
\tserverless deploy
"""

TEST_SAMPLE = """\
import json
from handler import health

def test_health_ok():
    resp = health({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
"""

class CodeGeneratorAgent:
    """
    Reads an OpenAPI file and scaffolds a minimal AWS Lambda API project.
    """
    def __init__(self, openapi_path: str, service_dir: str = "services/customer-alerts", region: str = "us-east-1"):
        self.openapi_path = Path(openapi_path)
        self.service_dir = Path(service_dir)
        self.region = region

    def run(self, input: Dict):
        """
        input may include overrides like:
        {
          "service_name": "customer-alerts",
          "runtime": "lambda"
        }
        """
        if not self.openapi_path.exists():
            raise FileNotFoundError(f"OpenAPI not found: {self.openapi_path}")

        self.service_dir.mkdir(parents=True, exist_ok=True)
        openapi = yaml.safe_load(self.openapi_path.read_text(encoding="utf-8"))
        base_path = self._infer_base_path(openapi)
        service_name = input.get("service_name", "customer-alerts")

        # 1) Create handler
        (self.service_dir / "handler.py").write_text(LAMBDA_HANDLER_TEMPLATE, encoding="utf-8")

        # 2) Map OpenAPI paths -> lambda routes (basic GET/POST scaffolding)
        dynamic_functions = self._generate_routes(openapi, base_path)

        # 3) serverless.yml for quick deploy
        serverless_yaml = SERVERLESS_YAML_TEMPLATE.format(
            service_name=service_name,
            region=self.region,
            base_path=base_path,
            dynamic_functions=dynamic_functions
        )
        (self.service_dir / "serverless.yml").write_text(serverless_yaml, encoding="utf-8")

        # 4) dependencies, tests, makefile
        (self.service_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
        tests_dir = self.service_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test_health.py").write_text(TEST_SAMPLE, encoding="utf-8")
        (self.service_dir / "Makefile").write_text(MAKEFILE, encoding="utf-8")

        # 5) Echo summary
        return {
            "status": "ok",
            "service_dir": str(self.service_dir),
            "routes": self._summarize_routes(openapi)
        }

    def _infer_base_path(self, openapi: Dict) -> str:
        # Try servers[0].url or default to /api
        servers = openapi.get("servers") or []
        if servers:
            url = servers[0].get("url", "/api")
            return url if url.startswith("/") else f"/{url}"
        return "/api"

    def _generate_routes(self, openapi: Dict, base_path: str) -> str:
        """
        Returns YAML fragment for dynamic functions based on OpenAPI paths.
        For demo purposes we route to a generic not_implemented handler and create stubs.
        """
        paths = openapi.get("paths", {})
        lines = []
        for route, methods in paths.items():
            if route == "/health":
                # already added
                continue
            for method, meta in methods.items():
                method = method.lower()
                func_name = self._function_name(route, method)
                lines.append(f"  {func_name}:")
                lines.append(f"    handler: handler.not_implemented")
                lines.append(f"    events:")
                lines.append(f"      - http:")
                lines.append(f"          path: {base_path}{route}")
                lines.append(f"          method: {method}")
        return "\n".join(lines) + ("\n" if lines else "")

    def _function_name(self, route: str, method: str) -> str:
        safe = route.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        safe = safe if safe else "root"
        return f"{method}_{safe}"

    def _summarize_routes(self, openapi: Dict):
        summary = []
        for route, methods in (openapi.get("paths") or {}).items():
            for m in methods.keys():
                summary.append(f"{m.upper()} {route}")
        return summary