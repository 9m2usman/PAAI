
from app.core.llm_client import generate_response
from app.memory.memory_manager import MemoryManager
from app.memory.memory_updater import propose_memory_updates
from app.memory.memory_updater import (propose_memory_updates,approve_memory_suggestion)
from app.memory.memory_updater import approve_memory_suggestion
from app.memory.memory_updater import approve_memory_suggestion

# STEP 1: Initialize the personalized agent

class PersonalizedAgent:

    def __init__(self):
        self.memory_manager = MemoryManager()


    # STEP 2: Start a conversation

    def start_chat(self, user_id, conversation_id):
        self.memory_manager.start_chat(
            user_id,
            conversation_id
        )


    # STEP 3: Process a user's message

    def chat(self, user_id, conversation_id, user_message):

        messages = self.memory_manager.build_llm_context(
            user_id,
            conversation_id,
            user_message
        )

        # STEP 4: Generate the response

        assistant_response = generate_response(messages)

        # STEP 5: Save the conversation exchange

        self.memory_manager.save_exchange(
            user_id,
            conversation_id,
            user_message,
            assistant_response
        )

        # STEP 6: Generate memory suggestions

        memory_suggestions = []

        try:
            memory_suggestions = propose_memory_updates(
                user_message
            )
        except Exception as error:
            print("Memory extraction failed:", error)

        # STEP 7: Return response and suggestions

        return {
            "user_id": user_id,
            "response": assistant_response,
            "memory_suggestions": memory_suggestions
        }


    # STEP 8: Approve and save a memory

    def approve_memory(self, user_id, memory, approved=True):
        return approve_memory_suggestion(
            user_id,
            memory,
            approved
        )
