
import json

from app.core.llm_client import generate_response


# STEP 1: Define the output structure

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string"
                },
                "action": {
                    "type": "string",
                    "enum": ["none", "inspect_files"]
                },
                "requires_tool": {
                    "type": "boolean"
                }
            },
            "required": [
                "intent",
                "action",
                "requires_tool"
            ],
            "additionalProperties": False
        }
    }
}


# STEP 2: Ask the LLM to classify the request

def analyze_request(user_request):

    messages = [
        {
            "role": "system",
            "content": (
                "You are PAAI's request analysis component. "
                "Analyze the user's request and return a structured decision. "
                "Use action 'inspect_files' when the user asks to inspect, "
                "list, or examine project files. "
                "For other requests, use action 'none'. "
                "Set requires_tool to true only when action is inspect_files. "
                "Return only the requested structured response."
            )
        },
        {
            "role": "user",
            "content": user_request
        }
    ]

    # STEP 3: Request a schema-constrained response

    response = generate_response(
        messages,
        response_format=RESPONSE_SCHEMA
    )

    # STEP 4: Convert JSON text into a Python dictionary

    try:
        decision = json.loads(response)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The LLM returned invalid JSON."
        ) from error

    # STEP 5: Validate the response before using it

    if not isinstance(decision, dict):
        raise RuntimeError("The LLM response must be a JSON object.")

    if not isinstance(decision.get("intent"), str):
        raise RuntimeError("Invalid intent field.")

    if decision.get("action") not in ["none", "inspect_files"]:
        raise RuntimeError("Invalid action.")

    if not isinstance(decision.get("requires_tool"), bool):
        raise RuntimeError("Invalid requires_tool field.")

    return decision


# STEP 6: Run the structured agent

if __name__ == "__main__":

    print("PAAI Structured Response Agent")

    while True:

        user_request = input("\nYou: ").strip()

        if user_request.lower() == "exit":
            print("PAAI: Goodbye!")
            break

        if not user_request:
            print("Please enter a request.")
            continue

        try:

            result = analyze_request(user_request)

            print("\nStructured Decision:")
            print(json.dumps(result, indent=4))

            print("\nPython Data Type:", type(result).__name__)

        except (ValueError, RuntimeError) as error:

            print("\nPAAI Error:", error)
