
import json

from app.core.llm_client import generate_completion

from app.core.agent_state import (
    create_agent_state,
    update_task_status,
    update_execution_round,
    add_tool_result,
    add_agent_error,
    set_final_response,
    display_agent_state
)

from app.tools.tool_registry import (
    AVAILABLE_TOOLS,
    execute_tool
)


# STEP 1: Define the agent's instructions

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are PAAI, a personal AI assistant. "
        "Use available tools when the user's request requires them. "
        "You may request multiple tools when necessary. "
        "Never claim you used a tool unless a tool result was provided. "
        "Explain the results clearly."
    )
}


# STEP 2: Set execution safety limits

MAX_TOOL_ROUNDS = 3


# STEP 3: Run the agent

def run_agent(user_request):

    # Create a separate state for this task

    state = create_agent_state(user_request)

    update_task_status(state, "running")

    messages = [
        SYSTEM_MESSAGE.copy(),
        {
            "role": "user",
            "content": user_request
        }
    ]

    try:

        # STEP 4: Start the execution loop

        for round_number in range(1, MAX_TOOL_ROUNDS + 1):

            update_execution_round(state, round_number)

            print(f"\nExecution round: {round_number}")

            assistant_message = generate_completion(
                messages,
                tools=AVAILABLE_TOOLS,
                tool_choice="auto"
            )

            # STEP 5: Check whether another tool is required

            if not assistant_message.tool_calls:

                final_response = assistant_message.content or (
                    "The agent completed without a text response."
                )

                set_final_response(state, final_response)

                update_task_status(state, "completed")

                return final_response, state

            # STEP 6: Save the assistant's tool requests

            messages.append(
                assistant_message.model_dump(exclude_none=True)
            )

            # STEP 7: Execute requested tools

            for tool_call in assistant_message.tool_calls:

                tool_name = tool_call.function.name

                try:

                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                    result = execute_tool(
                        tool_name,
                        arguments
                    )

                    tool_result = {
                        "success": True,
                        "data": result
                    }

                    add_tool_result(
                        state,
                        tool_name,
                        True,
                        result
                    )

                except Exception as error:

                    add_agent_error(state, error)

                    tool_result = {
                        "success": False,
                        "error": str(error)
                    }

                    add_tool_result(
                        state,
                        tool_name,
                        False,
                        str(error)
                    )

                # STEP 8: Send the tool result back to the LLM

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })

        # STEP 9: Stop when the execution limit is reached

        final_response = (
            "PAAI stopped because it reached the maximum "
            "number of tool execution rounds."
        )

        set_final_response(state, final_response)

        update_task_status(state, "limit_reached")

        return final_response, state

    except Exception as error:

        add_agent_error(state, error)

        update_task_status(state, "failed")

        raise


# STEP 10: Start the application

if __name__ == "__main__":

    print("PAAI Agent with Task State")
    print("Type 'exit' to stop.")

    while True:

        user_request = input("\nYou: ").strip()

        if user_request.lower() == "exit":
            print("PAAI: Goodbye!")
            break

        if not user_request:
            continue

        try:

            response, state = run_agent(user_request)

            print("\nPAAI:", response)

            display_agent_state(state)

        except (ValueError, RuntimeError) as error:

            print("\nPAAI Error:", error)
