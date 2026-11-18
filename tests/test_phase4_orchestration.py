
import unittest
from unittest.mock import patch

from app.orchestration.agent_registry import AgentRegistry
from app.orchestration.agent_communication import AgentCommunication
from app.orchestration.shared_state import SharedTaskState
from app.orchestration.failure_manager import FailureManager
from app.orchestration.task_delegator import TaskDelegator

from app.agents.specialized_agents import (
    ResearchAgent,
    AnalysisAgent,
    WritingAgent
)

from app.agents.supervisor_agent import SupervisorAgent


class FakeAgent:

    def __init__(self, name, result="Task completed", failures=0):
        self.name = name
        self.result = result
        self.failures = failures
        self.calls = 0

    def run(self, user_id, task_id, instruction, context):
        self.calls += 1

        if self.calls <= self.failures:
            raise RuntimeError("Simulated agent failure.")

        return self.result


class TestAgentRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = AgentRegistry()

    def test_register_and_retrieve_agent(self):
        agent = FakeAgent("research_agent")

        self.registry.register_agent(agent)

        self.assertTrue(
            self.registry.has_agent("research_agent")
        )

        self.assertIs(
            self.registry.get_agent("research_agent"),
            agent
        )

    def test_list_registered_agents(self):
        self.registry.register_agent(
            FakeAgent("research_agent")
        )

        self.registry.register_agent(
            FakeAgent("analysis_agent")
        )

        self.assertEqual(
            self.registry.list_agents(),
            ["research_agent", "analysis_agent"]
        )

    def test_duplicate_agent_is_rejected(self):
        self.registry.register_agent(
            FakeAgent("research_agent")
        )

        with self.assertRaises(ValueError):
            self.registry.register_agent(
                FakeAgent("research_agent")
            )

    def test_invalid_agent_is_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register_agent(object())

    def test_missing_agent_is_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.get_agent("unknown_agent")


class TestAgentCommunication(unittest.TestCase):

    def setUp(self):
        self.communication = AgentCommunication()

    def test_create_valid_message(self):
        message = self.communication.create_message(
            "supervisor_agent",
            "research_agent",
            "task_001",
            "Research this topic."
        )

        self.assertTrue(
            self.communication.validate_message(message)
        )

    def test_message_contains_required_fields(self):
        message = self.communication.create_message(
            "research_agent",
            "supervisor_agent",
            "task_001",
            "Research completed."
        )

        self.assertEqual(
            set(message.keys()),
            {
                "message_id",
                "sender",
                "receiver",
                "task_id",
                "content"
            }
        )

    def test_invalid_message_is_rejected(self):
        with self.assertRaises(ValueError):
            self.communication.validate_message(
                {"sender": "research_agent"}
            )

    def test_empty_message_content_is_rejected(self):
        with self.assertRaises(ValueError):
            self.communication.create_message(
                "supervisor_agent",
                "research_agent",
                "task_001",
                ""
            )


class TestSharedTaskState(unittest.TestCase):

    def setUp(self):
        self.state = SharedTaskState()

    def test_create_and_retrieve_task(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "Prepare a report."
        )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["user_id"], "user_a")

    def test_update_task_status(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "Prepare a report."
        )

        self.state.update_status(
            "user_a",
            "task_001",
            "completed"
        )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(task["status"], "completed")

    def test_add_subtask_and_result(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "Prepare a report."
        )

        self.state.add_subtask(
            "user_a",
            "task_001",
            {
                "subtask_id": "step_1",
                "agent": "research_agent",
                "status": "pending"
            }
        )

        self.state.update_subtask(
            "user_a",
            "task_001",
            "step_1",
            "completed"
        )

        self.state.add_result(
            "user_a",
            "task_001",
            "research_agent",
            "Research completed."
        )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(
            task["subtasks"][0]["status"],
            "completed"
        )

        self.assertEqual(
            task["results"]["research_agent"],
            "Research completed."
        )

    def test_user_task_isolation(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "User A task."
        )

        self.state.create_task(
            "user_b",
            "task_001",
            "User B task."
        )

        self.state.add_result(
            "user_a",
            "task_001",
            "research_agent",
            "Private result A"
        )

        self.state.add_result(
            "user_b",
            "task_001",
            "research_agent",
            "Private result B"
        )

        task_a = self.state.get_task(
            "user_a",
            "task_001"
        )

        task_b = self.state.get_task(
            "user_b",
            "task_001"
        )

        self.assertEqual(
            task_a["results"]["research_agent"],
            "Private result A"
        )

        self.assertEqual(
            task_b["results"]["research_agent"],
            "Private result B"
        )

    def test_returned_task_is_a_copy(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "Original request."
        )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        task["status"] = "modified"

        original = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(original["status"], "pending")

    def test_duplicate_task_is_rejected(self):
        self.state.create_task(
            "user_a",
            "task_001",
            "First task."
        )

        with self.assertRaises(ValueError):
            self.state.create_task(
                "user_a",
                "task_001",
                "Duplicate task."
            )

    def test_invalid_user_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.state.create_task(
                "",
                "task_001",
                "Some task."
            )


class TestFailureManager(unittest.TestCase):

    def setUp(self):
        self.manager = FailureManager(max_attempts=2)

    def test_successful_execution(self):
        agent = FakeAgent("research_agent")

        result = self.manager.execute_agent(
            agent,
            "user_a",
            "task_001",
            "Research topic.",
            {}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["attempts"], 1)

    def test_failed_first_attempt_then_success(self):
        agent = FakeAgent(
            "research_agent",
            failures=1
        )

        result = self.manager.execute_agent(
            agent,
            "user_a",
            "task_001",
            "Research topic.",
            {}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["attempts"], 2)

    def test_all_attempts_fail(self):
        agent = FakeAgent(
            "research_agent",
            failures=5
        )

        result = self.manager.execute_agent(
            agent,
            "user_a",
            "task_001",
            "Research topic.",
            {}
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["attempts"], 2)
        self.assertIsNotNone(result["error"])

    def test_empty_agent_result_is_rejected(self):
        agent = FakeAgent(
            "research_agent",
            result=""
        )

        result = self.manager.execute_agent(
            agent,
            "user_a",
            "task_001",
            "Research topic.",
            {}
        )

        self.assertFalse(result["success"])


class TestSpecializedAgents(unittest.TestCase):

    def test_all_specialized_agents_have_distinct_roles(self):
        agents = [
            ResearchAgent(),
            AnalysisAgent(),
            WritingAgent()
        ]

        self.assertEqual(
            len({agent.name for agent in agents}),
            3
        )

        self.assertEqual(
            {agent.name for agent in agents},
            {
                "research_agent",
                "analysis_agent",
                "writing_agent"
            }
        )

    @patch("app.agents.specialized_agents.generate_response")
    def test_agent_uses_existing_llm_client(self, mock_response):
        mock_response.return_value = "Research result."

        agent = ResearchAgent()

        result = agent.run(
            "user_a",
            "task_001",
            "Research AI agents.",
            {}
        )

        self.assertEqual(result, "Research result.")
        mock_response.assert_called_once()

    @patch("app.agents.specialized_agents.generate_response")
    def test_previous_results_are_passed_as_context(self, mock_response):
        mock_response.return_value = "Analysis completed."

        agent = AnalysisAgent()

        agent.run(
            "user_a",
            "task_001",
            "Analyze the research.",
            {
                "previous_results": {
                    "research_agent": "Research findings."
                }
            }
        )

        messages = mock_response.call_args[0][0]

        self.assertIn(
            "Research findings.",
            messages[1]["content"]
        )


class TestTaskDelegator(unittest.TestCase):

    def setUp(self):
        self.registry = AgentRegistry()
        self.state = SharedTaskState()

        self.research = FakeAgent(
            "research_agent",
            "Research findings."
        )

        self.analysis = FakeAgent(
            "analysis_agent",
            "Analysis findings."
        )

        self.registry.register_agent(self.research)
        self.registry.register_agent(self.analysis)

        self.delegator = TaskDelegator(
            self.registry,
            self.state
        )

        self.state.create_task(
            "user_a",
            "task_001",
            "Prepare a report."
        )

    def test_sequential_delegation(self):
        workflow = [
            {
                "agent": "research_agent",
                "instruction": "Research the topic."
            },
            {
                "agent": "analysis_agent",
                "instruction": "Analyze the research."
            }
        ]

        results = self.delegator.execute_workflow(
            "user_a",
            "task_001",
            "Prepare a report.",
            workflow
        )

        self.assertEqual(
            results["research_agent"],
            "Research findings."
        )

        self.assertEqual(
            results["analysis_agent"],
            "Analysis findings."
        )

        self.assertEqual(self.research.calls, 1)
        self.assertEqual(self.analysis.calls, 1)

    def test_task_is_marked_completed(self):
        self.delegator.execute_workflow(
            "user_a",
            "task_001",
            "Prepare a report.",
            [
                {
                    "agent": "research_agent",
                    "instruction": "Research the topic."
                }
            ]
        )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(task["status"], "completed")

    def test_agent_failure_marks_task_failed(self):
        failing_agent = FakeAgent(
            "research_agent",
            failures=5
        )

        registry = AgentRegistry()
        registry.register_agent(failing_agent)

        delegator = TaskDelegator(
            registry,
            self.state,
            FailureManager(max_attempts=2)
        )

        with self.assertRaises(RuntimeError):
            delegator.execute_workflow(
                "user_a",
                "task_001",
                "Prepare a report.",
                [
                    {
                        "agent": "research_agent",
                        "instruction": "Research the topic."
                    }
                ]
            )

        task = self.state.get_task(
            "user_a",
            "task_001"
        )

        self.assertEqual(task["status"], "failed")
        self.assertTrue(task["errors"])


class TestSupervisorAgent(unittest.TestCase):

    @patch(
        "app.agents.specialized_agents.generate_response"
    )
    def test_complete_multi_agent_workflow(self, mock_response):
        mock_response.side_effect = [
            "Research findings.",
            "Analysis findings.",
            "Final report."
        ]

        supervisor = SupervisorAgent()

        result = supervisor.run(
            "user_a",
            "Research AI agents and prepare a report."
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"], "Final report.")

        self.assertEqual(
            set(result["agent_results"].keys()),
            {
                "research_agent",
                "analysis_agent",
                "writing_agent"
            }
        )

        task = result["task_state"]

        self.assertEqual(task["status"], "completed")
        self.assertEqual(len(task["subtasks"]), 3)
        self.assertEqual(len(task["messages"]), 6)

        for subtask in task["subtasks"]:
            self.assertEqual(
                subtask["status"],
                "completed"
            )

        self.assertEqual(mock_response.call_count, 3)

    @patch(
        "app.agents.specialized_agents.generate_response"
    )
    def test_previous_agents_results_reach_later_agents(
        self,
        mock_response
    ):
        mock_response.side_effect = [
            "Research findings.",
            "Analysis findings.",
            "Final report."
        ]

        supervisor = SupervisorAgent()

        supervisor.run(
            "user_a",
            "Prepare a report about AI."
        )

        calls = mock_response.call_args_list

        analysis_message = calls[1][0][0][1]["content"]
        writing_message = calls[2][0][0][1]["content"]

        self.assertIn(
            "Research findings.",
            analysis_message
        )

        self.assertIn(
            "Research findings.",
            writing_message
        )

        self.assertIn(
            "Analysis findings.",
            writing_message
        )

    @patch(
        "app.agents.specialized_agents.generate_response",
        side_effect=RuntimeError("Simulated LLM failure.")
    )
    def test_supervisor_handles_agent_failure(self, mock_response):
        supervisor = SupervisorAgent()

        result = supervisor.run(
            "user_a",
            "Prepare a report."
        )

        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["result"])
        self.assertIsNotNone(result["error"])

        self.assertEqual(
            result["task_state"]["status"],
            "failed"
        )

    def test_supervisor_rejects_invalid_user(self):
        supervisor = SupervisorAgent()

        with self.assertRaises(ValueError):
            supervisor.run(
                "",
                "Prepare a report."
            )

    @patch(
        "app.agents.specialized_agents.generate_response"
    )
    def test_same_supervisor_serves_separate_users(
        self,
        mock_response
    ):
        mock_response.side_effect = [
            "User A research.",
            "User A analysis.",
            "User A report.",
            "User B research.",
            "User B analysis.",
            "User B report."
        ]

        supervisor = SupervisorAgent()

        result_a = supervisor.run(
            "user_a",
            "Prepare User A report."
        )

        result_b = supervisor.run(
            "user_b",
            "Prepare User B report."
        )

        self.assertEqual(result_a["status"], "completed")
        self.assertEqual(result_b["status"], "completed")

        self.assertEqual(
            result_a["user_id"],
            "user_a"
        )

        self.assertEqual(
            result_b["user_id"],
            "user_b"
        )

        self.assertNotEqual(
            result_a["task_id"],
            result_b["task_id"]
        )


if __name__ == "__main__":
    unittest.main()
