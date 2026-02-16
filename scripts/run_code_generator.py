import os
import sys
import json

# Ensure the repo root is on sys.path (so 'agents' can be imported)
sys.path.append(os.path.abspath("."))

from agents.code_generator.agent import CodeGeneratorAgent

if __name__ == "__main__":
    openapi_path = "docs/specs/TKT-DEMO-openapi.yaml"  # adjust if using a different ticket id
    agent = CodeGeneratorAgent(
        openapi_path=openapi_path,
        service_dir="services/customer-alerts",
        region="us-east-1"
    )
    out = agent.run({"service_name": "customer-alerts"})
    print(json.dumps(out, indent=2))