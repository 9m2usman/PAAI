
import unittest
from unittest.mock import patch

from app.tools.tool_registry import (
    AVAILABLE_TOOLS,
    TOOL_REGISTRY,
    execute_tool
)


class TestToolRegistry(unittest.TestCase):

    # STEP 1: Confirm only registered tools are exposed

    def test_available_tools_match_registry(self):

        registered_names = list(TOOL_REGISTRY.keys())

        available_names = [
            tool["function"]["name"]
            for tool in AVAILABLE_TOOLS
        ]

        self.assertEqual(available_names, registered_names)

    # STEP 2: Reject unknown tools

    def test_unknown_tool_is_rejected(self):

        with self.assertRaises(ValueError):
            execute_tool("delete_everything", {})

    # STEP 3: Reject invalid argument types

    def test_invalid_argument_type_is_rejected(self):

        with self.assertRaises(ValueError):
            execute_tool("list_project_files", "invalid")

    # STEP 4: Reject unexpected arguments

    def test_unexpected_arguments_are_rejected(self):

        with self.assertRaises(ValueError):
            execute_tool(
                "list_project_files",
                {"directory": "C:\\"}
            )

    # STEP 5: Execute a registered tool successfully

    def test_registered_tool_executes(self):

        expected_result = {
            "project": "PAAI",
            "total_files_found": 2,
            "files": ["app/main.py", "README.md"],
            "truncated": False
        }

        test_registry = {
            **TOOL_REGISTRY["list_project_files"],
            "handler": lambda: expected_result
        }

        with patch.dict(
            TOOL_REGISTRY,
            {"list_project_files": test_registry}
        ):

            result = execute_tool(
                "list_project_files",
                {}
            )

        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
