
import json

from app.core.llm_client import generate_response
from app.tools.tool_registry import TOOL_REGISTRY


# STEP 1: Define planning limits

MAX_PLAN_STEPS = 5


# STEP 2: Build the allowed tool names

ALLOWED_TOOLS = ["none"] + list(TOOL_REGISTRY.keys())


# STEP 3: Define the structured plan schema

PLAN_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_task_plan",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {
                                "type": "integer"
                            },
                            "description": {
                                "type": "string"
                            },
                            "tool": {
                                "type": "string",
                                "enum": ALLOWED_TOOLS
                            },
                            "requires_tool": {
                                "type": "boolean"
                            }
                        },
                        "required": [
                            "step_number",
                            "description",
                            "tool",
                            "requires_tool"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["goal", "steps"],
            "additionalProperties": False
        }
    }
}


# STEP 4: Validate the generated plan

def validate_task_plan(plan):

    if not isinstance(plan, dict):
        raise ValueError("The generated plan must be an object.")

    goal = plan.get("goal")
    steps = plan.get("steps")

    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("The plan must contain a valid goal.")

    if not isinstance(steps, list) or not steps:
        raise ValueError("The plan must contain at least one step.")

    if len(steps) > MAX_PLAN_STEPS:
        raise ValueError("The plan exceeds the maximum step limit.")

    for index, step in enumerate(steps, start=1):

        if not isinstance(step, dict):
            raise ValueError("Every plan step must be an object.")

        if step.get("step_number") != index:
            raise ValueError("Plan step numbers must be sequential.")

        description = step.get("description")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("Every step must have a description.")

        tool = step.get("tool")
        requires_tool = step.get("requires_tool")

        if tool not in ALLOWED_TOOLS:
            raise ValueError("The plan contains an unregistered tool.")

        if not isinstance(requires_tool, bool):
            raise ValueError("requires_tool must be a boolean.")

        if requires_tool and tool == "none":
            raise ValueError("A required tool must be registered.")

        if not requires_tool and tool != "none":
            raise ValueError(
                "A non-tool step must use tool='none'."
            )

    return plan


# STEP 5: Generate and validate a task plan

def create_task_plan(user_request):

    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("The user request cannot be empty.")

    messages = [
        {
            "role": "system",
            "content": (
                "You are PAAI's task planner. "
                "Break the user's request into clear, sequential steps. "
                "Use only registered tools when necessary. "
                "Use tool='none' for reasoning steps. "
                "Never invent tool names. "
                "Create between 1 and 5 steps."
            )
        },
        {
            "role": "user",
            "content": user_request
        }
    ]

    response = generate_response(
        messages,
        response_format=PLAN_SCHEMA
    )

    try:
        plan = json.loads(response)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "The model returned invalid JSON for the task plan."
        ) from error

    return validate_task_plan(plan)
