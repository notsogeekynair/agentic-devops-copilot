class SupervisorAgent:
    def __init__(self, agent_runtime):
        self.runtime = agent_runtime

    def handle_ticket(self, ticket):
        # 1. Break task into subtasks
        subtasks = self.create_subtasks(ticket)

        # 2. Route subtasks to the right worker agent
        results = []
        for task in subtasks:
            result = self.runtime.delegate(
                worker_id=task["worker"],
                input=task["payload"]
            )
            results.append(result)

        # 3. Aggregate results
        return {
            "status": "completed",
            "outputs": results
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