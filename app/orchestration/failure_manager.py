class FailureManager:

    def __init__(self, max_attempts=2):
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("Invalid maximum attempts.")

        self.max_attempts = max_attempts

    def execute_agent(
        self,
        agent,
        user_id,
        task_id,
        instruction,
        context
    ):
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = agent.run(
                    user_id,
                    task_id,
                    instruction,
                    context
                )

                if not isinstance(result, str) or not result.strip():
                    raise ValueError("Agent returned an empty result.")

                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt,
                    "error": None
                }

            except Exception as error:
                last_error = str(error)

        return {
            "success": False,
            "result": None,
            "attempts": self.max_attempts,
            "error": last_error
        }