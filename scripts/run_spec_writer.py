import json
from agents.spec-writer.agent import SpecWriterAgent

if __name__ == "__main__":
    ticket = {
        "id": "TKT-DEMO",
        "title": "Customer Alerts microservice",
        "description": "Backend microservice to manage user alerts: create, list, mark as read. Expose REST APIs.",
        "acceptance_criteria": [
            "POST /alerts -> 201 with alertId",
            "GET /alerts?userId -> 200 list of alerts",
            "PATCH /alerts/{id} mark read -> 200"
        ],
        "constraints": [
            "JWT auth via API Gateway + Cognito",
            "DynamoDB single-table design preferred"
        ]
    }
    agent = SpecWriterAgent()
    out = agent.run({"ticket": ticket})
    print(json.dumps(out, indent=2))