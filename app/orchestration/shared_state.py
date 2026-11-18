import threading
import copy


class SharedTaskState:

    def __init__(self):
        self.tasks = {}
        self.lock = threading.RLock()

    def create_task(self, user_id, task_id, user_request):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Invalid user ID.")

        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Invalid task ID.")

        if not isinstance(user_request, str) or not user_request.strip():
            raise ValueError("Invalid user request.")

        key = (user_id, task_id)

        with self.lock:
            if key in self.tasks:
                raise ValueError("Task already exists.")

            self.tasks[key] = {
                "user_id": user_id,
                "task_id": task_id,
                "user_request": user_request,
                "status": "pending",
                "subtasks": [],
                "results": {},
                "messages": [],
                "errors": []
            }

    def get_task(self, user_id, task_id):
        key = (user_id, task_id)

        with self.lock:
            task = self.tasks.get(key)

            if task is None:
                return None

            return copy.deepcopy(task)

    def update_status(self, user_id, task_id, status):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            self.tasks[key]["status"] = status

    def add_subtask(self, user_id, task_id, subtask):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            self.tasks[key]["subtasks"].append(
                copy.deepcopy(subtask)
            )

    def update_subtask(self, user_id, task_id, subtask_id, status):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            for subtask in self.tasks[key]["subtasks"]:
                if subtask["subtask_id"] == subtask_id:
                    subtask["status"] = status
                    return

            raise ValueError("Subtask not found.")

    def add_result(self, user_id, task_id, agent_name, result):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            self.tasks[key]["results"][agent_name] = result

    def add_message(self, user_id, task_id, message):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            self.tasks[key]["messages"].append(
                copy.deepcopy(message)
            )

    def add_error(self, user_id, task_id, error):
        key = (user_id, task_id)

        with self.lock:
            if key not in self.tasks:
                raise ValueError("Task not found.")

            self.tasks[key]["errors"].append(str(error))