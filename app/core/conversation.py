# STEP 1: Define the system instruction

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are PAAI, a helpful personal AI assistant. "
        "Answer clearly and accurately. "
        "Use the conversation history to understand follow-up questions."
    )
}


# STEP 2: Set the conversation history limit

MAX_HISTORY_MESSAGES = 10


# STEP 3: Start a new conversation

def create_conversation():

    return [SYSTEM_MESSAGE.copy()]


# STEP 4: Add a message to the conversation

def add_message(conversation, role, content):

    conversation.append({
        "role": role,
        "content": content
    })


# STEP 5: Keep conversation history within the limit

def trim_conversation(conversation):

    system_message = conversation[0]

    recent_messages = conversation[1:]

    recent_messages = recent_messages[-MAX_HISTORY_MESSAGES:]

    return [system_message] + recent_messages
