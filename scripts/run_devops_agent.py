import os, sys, json
sys.path.append(os.path.abspath("."))

from agents.devops_iac.agent import DevOpsIacAgent

if __name__ == "__main__":
    agent = DevOpsIacAgent(cdk_dir="infra/cdk")
    out = agent.run({
        "region": "us-east-1",
        "service_dir": "services/customer-alerts"
    })
    print(json.dumps(out, indent=2))
