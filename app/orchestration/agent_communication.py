import uuid


class AgentCommunication:

    def create_message(
        self,
        sender,
        receiver,
        task_id,
        content
    ):
        if not all(
            isinstance(value, str) and value.strip()
            for value in [sender, receiver, task_id]
        ):
            raise ValueError("Invalid message identifiers.")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Message content cannot be empty.")

        return {
            "message_id": str(uuid.uuid4()),
            "sender": sender,
            "receiver": receiver,
            "task_id": task_id,
            "content": content
        }

    def validate_message(self, message):
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary.")

        required_fields = {
            "message_id",
            "sender",
            "receiver",
            "task_id",
            "content"
        }

        if set(message.keys()) != required_fields:
            raise ValueError("Invalid message structure.")

        for field in required_fields:
            if not isinstance(message[field], str):
                raise ValueError(f"Invalid message field: {field}")

            if not message[field].strip():
                raise ValueError(f"Empty message field: {field}")

        return True