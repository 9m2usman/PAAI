
# STEP 1: Create a new task state

def create_agent_state(user_request):

    return {
        "task": user_request,
        "status": "created",
        "current_round": 0,
        "plan": [],
        "step_results": [],
        "tool_results": [],
        "errors": [],
        "final_response": None
    }


# STEP 2: Update task status

def update_task_status(state, status):

    state["status"] = status


# STEP 3: Update execution round

def update_execution_round(state, round_number):

    state["current_round"] = round_number


# STEP 4: Save the generated plan

def save_task_plan(state, plan):

    state["plan"] = plan


# STEP 5: Record the result of a plan step

def add_step_result(state, step_number, description, status, result=None):

    state["step_results"].append({
        "step_number": step_number,
        "description": description,
        "status": status,
        "result": result
    })


# STEP 6: Save a tool execution result

def add_tool_result(state, tool_name, success, result):

    state["tool_results"].append({
        "tool": tool_name,
        "success": success,
        "result": result
    })


# STEP 7: Record an execution error

def add_agent_error(state, error):

    state["errors"].append(str(error))


# STEP 8: Save the final response

def set_final_response(state, response):

    state["final_response"] = response


# STEP 9: Display the task summary

def display_agent_state(state):

    print("\n========== AGENT STATE ==========")

    print("Task:", state["task"])
    print("Status:", state["status"])
    print("Execution rounds:", state["current_round"])
    print("Planned steps:", len(state["plan"]))
    print("Recorded steps:", len(state["step_results"]))
    print("Tools executed:", len(state["tool_results"]))
    print("Errors:", len(state["errors"]))

    for step in state["step_results"]:

        print(
            f"\nStep {step['step_number']}: "
            f"{step['status']}"
        )

        print("Description:", step["description"])

    if state["errors"]:

        print("\nExecution errors:")

        for error in state["errors"]:
            print("-", error)

    print("================================")
