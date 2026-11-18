
from app.tools.file_tools import list_project_files


# STEP 1: Validate arguments for the file listing tool

def validate_list_project_files_arguments(arguments):

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    if arguments:
        raise ValueError(
            "list_project_files does not accept any arguments."
        )

    return True


# STEP 2: Define the trusted tool registry

TOOL_REGISTRY = {
    "list_project_files": {
        "description": (
            "List files in the PAAI project directory. "
            "This tool is read-only."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        },
        "handler": list_project_files,
        "validate": validate_list_project_files_arguments
    }
}


# STEP 3: Generate the tool definitions sent to the LLM

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_details["description"],
            "parameters": tool_details["parameters"]
        }
    }
    for tool_name, tool_details in TOOL_REGISTRY.items()
]


# STEP 4: Execute only trusted, registered tools

def execute_tool(tool_name, arguments):

    if not isinstance(tool_name, str):
        raise ValueError("Tool name must be a string.")

    if tool_name not in TOOL_REGISTRY:
        raise ValueError("Tool is not registered.")

    tool = TOOL_REGISTRY[tool_name]

    # Validate arguments before executing the function
    tool["validate"](arguments)

    # Execute only the trusted function stored in the registry
    return tool["handler"]()
