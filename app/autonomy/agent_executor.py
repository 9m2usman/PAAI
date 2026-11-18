from app.core.llm_client import generate_response

class ReasoningGoalExecutor:
    """Safe default executor: performs bounded reasoning only, never external actions."""
    def __call__(self, description, limits):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are PAAI's autonomous reasoning worker. "
                    "Work only on the supplied user goal. You have no external tools "
                    "and must not claim to have sent messages, changed files, made "
                    "purchases, or performed actions outside this response. "
                    "Return a useful result, identify uncertainty, and state any "
                    "human action still required. Keep the work within the supplied "
                    "step and runtime budgets."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Goal to work on:\n" + description
                    + "\n\nExecution limits:\n"
                    + str(limits)
                ),
            },
        ]
        return generate_response(messages)
