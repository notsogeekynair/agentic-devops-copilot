from agents.spec_writer.agent import SpecWriterAgent

class SupervisorAgent:
    def __init__(self, agent_runtime=None):
        self.runtime = agent_runtime
        self.spec_writer = SpecWriterAgent()

    def handle_ticket(self, ticket):
        # 1) Always start with spec generation
        spec_result = self.spec_writer.run({"ticket": ticket})

        # 2) Pass paths forward as context to other agents
        context = {
            "ticket": ticket,
            "spec_md_path": spec_result["outputs"]["spec_md"],
            "openapi_path": spec_result["outputs"]["openapi_yaml"]
        }

        # Example: you can still delegate to your runtime if you wire it later
        results = [ {"agent": "spec_writer_agent", "result": spec_result} ]
        # TODO: delegate to codegen/devops/deploy/metrics with 'context'

        return {
            "status": "completed",
            "outputs": results,
            "context": context
        }


    def create_subtasks(self, ticket):
        return [
            {
                "worker": "spec_writer_agent",
                "payload": {"ticket": ticket}
            },
            {
                "worker": "code_generator_agent",
                "payload": {"ticket": ticket}
            },
            {
                "worker": "devops_iac_agent",
                "payload": {"ticket": ticket}
            },
            {
                "worker": "deployment_agent",
                "payload": {"ticket": ticket}
            },
            {
                "worker": "metrics_agent",
                "payload": {"ticket": ticket}
            }
        ]