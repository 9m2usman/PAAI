
MAX_CONVERSATION_MESSAGES = 20

# STEP 1: Create the short-term memory container

def create_short_term_memory():
    return {}


# STEP 2: Validate identity and conversation ID

def validate_ids(user_id, conversation_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid user_id is required.")

    if not isinstance(conversation_id, str) or not conversation_id.strip():
        raise ValueError("A valid conversation_id is required.")


# STEP 3: Start a conversation

def start_conversation(memory, user_id, conversation_id):
    validate_ids(user_id, conversation_id)

    if user_id not in memory:
        memory[user_id] = {}

    memory[user_id][conversation_id] = []


# STEP 4: Add a message to a conversation

def add_conversation_message(
    memory, user_id, conversation_id, role, content
):
    validate_ids(user_id, conversation_id)

    if user_id not in memory:
        raise ValueError("User conversation does not exist.")

    if conversation_id not in memory[user_id]:
        raise ValueError("Conversation does not exist.")

    if role not in {"user", "assistant"}:
        raise ValueError("Invalid conversation message role.")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Message content cannot be empty.")

    messages = memory[user_id][conversation_id]

    messages.append({"role": role, "content": content})

    if len(messages) > MAX_CONVERSATION_MESSAGES:
        del messages[:-MAX_CONVERSATION_MESSAGES]

# STEP 5: Retrieve conversation history

def get_conversation(memory, user_id, conversation_id):
    validate_ids(user_id, conversation_id)

    if user_id not in memory:
        return []

    if conversation_id not in memory[user_id]:
        return []

    return [
        message.copy()
        for message in memory[user_id][conversation_id]
    ]


# STEP 6: Clear a conversation

def clear_conversation(memory, user_id, conversation_id):
    validate_ids(user_id, conversation_id)

    if user_id not in memory:
        return False

    if conversation_id not in memory[user_id]:
        return False

    del memory[user_id][conversation_id]
    return True
