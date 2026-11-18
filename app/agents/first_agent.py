# STEP 1: Define the agent's tools

def get_user_name():
    return "Usman"

def get_current_task():
    return "Build a personal autonomous AI agent system"


# STEP 2: Define the agent

def run_agent(user_request):

    print("Agent received:", user_request)

    # STEP 3: Decide which tool to use

    if "name" in user_request.lower():
        result = get_user_name()

    elif "task" in user_request.lower():
        result = get_current_task()

    else:
        result = "I don't have a suitable tool for this request."

    # STEP 4: Observe and return the result

    print("Agent result:", result)

    return result


# STEP 5: Run the agent

result = run_agent("What is my name?")

print("Returned value:", result)