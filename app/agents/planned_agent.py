import json

from app.core.llm_client import generate_response
from app.core.agent_state import (
    create_agent_state,
    update_task_status,
    update_execution_round,
    save_task_plan,
    add_step_result,
    add_tool_result,
    add_agent_error,
    set_final_response,
    display_agent_state
)
from app.agents.task_planner import create_task_plan
from app.tools.tool_registry import execute_tool


# STEP 1: Define independent execution limits

MAX_PLAN_STEPS = 5
MAX_TOOL_EXECUTIONS = 3


# STEP 2: Execute one reasoning step using previous evidence

def execute_reasoning_step(user_request, step, completed_results):

    messages = [
        {
            "role": "system",
            "content": (
                "You are PAAI's reasoning component. "
                "Execute only the current task step. "
                "Use the original request and previous execution results "
                "as context. Do not claim that external tools were used. "
                "Be accurate and clearly explain uncertainty."
            )
        },
        {
            "role": "user",
            "content": (
                "Original request:\n"
                + user_request
                + "\n\nCurrent step:\n"
                + step["description"]
                + "\n\nPrevious execution results:\n"
                + json.dumps(completed_results, indent=2)
                + "\n\nComplete this step and return its result."
            )
        }
    ]

    return generate_response(messages)


# STEP 3: Build a truthful fallback response

def build_fallback_response(state):

    completed_steps = [
        step for step in state["step_results"]
        if step["status"] == "completed"
    ]

    failed_steps = [
        step for step in state["step_results"]
        if step["status"] == "failed"
    ]

    response = [
        "PAAI execution report",
        "",
        f"Task: {state['task']}",
        f"Completed steps: {len(completed_steps)}",
        f"Failed steps: {len(failed_steps)}"
    ]

    if completed_steps:
        response.append("\nCompleted work:")
        for step in completed_steps:
            response.append(
                f"- Step {step['step_number']}: "
                f"{step['description']}"
            )

    if failed_steps:
        response.append("\nFailed work:")
        for step in failed_steps:
            response.append(
                f"- Step {step['step_number']}: "
                f"{step['description']}"
            )
            response.append(f"  Reason: {step['result']}")

    response.append(
        "\nPAAI could not generate its normal final summary. "
        "The execution records above preserve the available results."
    )

    return "\n".join(response)


# STEP 4: Count successfully completed steps

def count_completed_steps(state):

    return sum(
        1 for step in state["step_results"]
        if step["status"] == "completed"
    )


# STEP 5: Run the canonical planned agent runtime

def run_planned_agent(user_request):

    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("The user request cannot be empty.")

    state = create_agent_state(user_request)

    update_task_status(state, "planning")

    try:

        # STEP 6: Generate and validate the plan

        plan = create_task_plan(user_request)

        if len(plan["steps"]) > MAX_PLAN_STEPS:
            raise ValueError("The plan exceeds the execution limit.")

        save_task_plan(state, plan)

        update_task_status(state, "running")

        execution_results = []
        tool_execution_count = 0
        execution_stopped = False

        # STEP 7: Execute each planned step

        for step in plan["steps"]:

            step_number = step["step_number"]
            description = step["description"]

            update_execution_round(state, step_number)

            print(f"\nExecuting step {step_number}:")
            print(description)

            try:

                # STEP 8: Execute a registered tool

                if step["requires_tool"]:

                    if tool_execution_count >= MAX_TOOL_EXECUTIONS:
                        raise RuntimeError(
                            "Maximum tool execution limit reached."
                        )

                    tool_execution_count += 1

                    result = execute_tool(
                        step["tool"],
                        {}
                    )

                    add_tool_result(
                        state,
                        step["tool"],
                        True,
                        result
                    )

                    step_result = {
                        "step_number": step_number,
                        "description": description,
                        "type": "tool",
                        "status": "completed",
                        "result": result
                    }

                # STEP 9: Execute a reasoning step with one retry

                else:

                    MAX_REASONING_RETRIES = 1
                    result = None
                    last_error = None

                    for attempt in range(MAX_REASONING_RETRIES + 1):

                        try:
                            result = execute_reasoning_step(
                                user_request,
                                step,
                                execution_results
                            )

                            if not isinstance(result, str) or not result.strip():
                                raise RuntimeError(
                                    "The reasoning step returned an empty result."
                                )

                            last_error = None
                            break

                        except Exception as error:

                            last_error = error

                            if attempt < MAX_REASONING_RETRIES:
                                print(
                                    "\nReasoning step failed. "
                                    "Retrying once..."
                                )

                    if last_error is not None:
                        raise RuntimeError(
                            "Reasoning step failed after retry: "
                            + str(last_error)
                        ) from last_error

                    step_result = {
                        "step_number": step_number,
                        "description": description,
                        "type": "reasoning",
                        "status": "completed",
                        "result": result
                    }


                # STEP 10: Save successful execution evidence

                execution_results.append(step_result)

                add_step_result(
                    state,
                    step_number,
                    description,
                    "completed",
                    result
                )

            except Exception as error:

                error_message = str(error)

                add_agent_error(state, error_message)

                if step["requires_tool"]:
                    add_tool_result(
                        state,
                        step["tool"],
                        False,
                        error_message
                    )

                failed_result = {
                    "step_number": step_number,
                    "description": description,
                    "type": (
                        "tool" if step["requires_tool"]
                        else "reasoning"
                    ),
                    "status": "failed",
                    "error": error_message
                }

                execution_results.append(failed_result)

                add_step_result(
                    state,
                    step_number,
                    description,
                    "failed",
                    error_message
                )

                print("\nStep failed:", error_message)

                # Stop because later steps may depend on this result

                execution_stopped = True
                break

        # STEP 11: Prepare evidence for final synthesis

        execution_data = {
            "goal": plan["goal"],
            "planned_steps": plan["steps"],
            "execution_results": execution_results,
            "tool_executions": tool_execution_count,
            "execution_stopped": execution_stopped
        }

        # STEP 12: Generate the final response

        try:

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are PAAI. Produce a final report using "
                        "only the supplied execution evidence and "
                        "the user's original request. "
                        "Do not claim that an incomplete step succeeded. "
                        "Distinguish completed work, failed work, "
                        "and work that was never executed. "
                        "Never invent tool results."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Original request:\n"
                        + user_request
                        + "\n\nExecution evidence:\n"
                        + json.dumps(execution_data, indent=2)
                    )
                }
            ]

            final_response = generate_response(messages)

            if not isinstance(final_response, str) or not final_response.strip():
                raise RuntimeError(
                    "The final response was empty."
                )

        except Exception as error:

            add_agent_error(
                state,
                "Final response generation failed: " + str(error)
            )

            final_response = build_fallback_response(state)

        # STEP 13: Save final response and determine task status

        set_final_response(state, final_response)

        completed_count = count_completed_steps(state)

        if state["errors"]:

            if completed_count > 0:
                update_task_status(state, "partially_completed")
            else:
                update_task_status(state, "failed")

        else:
            update_task_status(state, "completed")

        return final_response, state

    except Exception as error:

        add_agent_error(state, error)
        update_task_status(state, "failed")

        raise


# STEP 14: Start the planned agent from the terminal

if __name__ == "__main__":

    print("PAAI Autonomous Agent Runtime")
    print("Type 'exit' to stop.")

    while True:

        user_request = input("\nYou: ").strip()

        if user_request.lower() == "exit":
            print("PAAI: Goodbye!")
            break

        if not user_request:
            continue

        try:

            response, state = run_planned_agent(user_request)

            print("\nPAAI:", response)

            display_agent_state(state)

        except (ValueError, RuntimeError) as error:

            print("\nPAAI Error:", error)
