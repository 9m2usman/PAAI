from app.core.llm_client import generate_response
from app.core.conversation import (
    create_conversation,
    add_message,
    trim_conversation
)


# STEP 1: Start the agent

def run_agent():

    print("PAAI LLM Agent")
    print("Conversation context is enabled.")
    print("Type 'exit' to stop.")

    # STEP 2: Create conversation history

    conversation = create_conversation()

    while True:

        user_request = input("\nYou: ").strip()

        # STEP 3: Check whether the user wants to exit

        if user_request.lower() == "exit":
            print("PAAI: Goodbye!")
            break

        if not user_request:
            print("PAAI: Please enter a message.")
            continue

        # STEP 4: Add the user's message to conversation history

        add_message(conversation, "user", user_request)

        # STEP 5: Send the conversation to the LLM

        try:

            response = generate_response(conversation)

            # STEP 6: Save the assistant's response

            add_message(conversation, "assistant", response)

            # STEP 7: Limit conversation history

            conversation = trim_conversation(conversation)

            print("\nPAAI:", response)

        except (ValueError, RuntimeError) as error:
            print("\nPAAI Error:", error)


# STEP 8: Run the application

if __name__ == "__main__":
    run_agent()
