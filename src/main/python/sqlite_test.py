import dataset
import ast
from openai import OpenAI
import json
import os

db = dataset.connect('sqlite:///mydatabase.db')

# Create tables for runs and for individual states
run_table = db['runs']
state_table = db['states']

client = OpenAI()

# Insert all runs in "runs" folder
# Get list of filenames from "runs/"
filenames = os.listdir("runs/")
for elem in filenames:
    print("Processing: ", elem)
    filename = elem.split(".txt")[0]
    with open("runs/" + filename + ".txt", "r") as file:
        trajectory_file = file.read()
    # Split into a list line by line
    trajectory = trajectory_file.split("\n")

    # Get the final state
    print(trajectory[-2])
    with open('prompts/system_analysis.txt', 'r') as file:
        system_prompt = file.read()
    system_prompt = system_prompt.replace('INSERT', trajectory[-2])
    print("System prompt: ", system_prompt)

    # Make a file to write to
    write_file = open("runs_processed/" + filename + ".txt", "w")

    # Create tool
    tools = [
        {
            "type": "function",
            "function": {
                "name": "store_state_action_rating",
                "description": "Store rating of bot action at a given state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rating": {
                            "type": "string",
                            "description": "Rating the bot action (-1 for bad, 1 for good, 0 for neutral)",
                            "enum": ["-1", "0", "1"]
                        },
                        "best_action": {"type": "string"},
                    },
                    "required": ["rating", "best_action"],
                },
            },
        }
    ]

    final_state = ast.literal_eval(trajectory[-2])
    # What is the key information we want to store? Just an overview of the key run details we want to filter by
    final_state_info = {
        "timestamp": filename,
        "act": final_state['game_state']['act'],
        "floor": final_state['game_state']['floor'],
        "class": final_state['game_state']['class'],
        "ascension_level": final_state['game_state']['ascension_level'],
        "act_boss": final_state['game_state']['act_boss'],
        "score": final_state['game_state']['screen_state']['score'],
        "victory": final_state['game_state']['screen_state']['victory'],
    }
    # Convert all lists to strings
    for key in final_state_info:
        if isinstance(final_state_info[key], list):
            final_state_info[key] = str(final_state_info[key])
    # Insert the run
    run_id = run_table.insert(final_state_info)
    print("Successfully inserted run with id: ", run_id)

    run_step = 0
    # Now loop through the trajectory and analyze each decision
    for i in range(len(trajectory) - 1):
        state = trajectory[i]
        # Check if its a bot action
        if "Bot response: " not in state:
            continue
        # Let's do the assessment of trajectory
        stripped_response = None
        try:
            prompt = "Evaluate this decision by the metagame bot: " + trajectory[i - 1] + "\n" + trajectory[i]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                tools=tools,
                tool_choice="required"
            )
            print("Response: ", response.choices[0].message.tool_calls[0].function.arguments)
            #split_response = json.dumps(response.choices[0].message.tool_calls[0].function.arguments)
            # Strip all newline chars from response
            stripped_response = str(response.choices[0].message.tool_calls[0].function.arguments).replace("\n", "")
            write_file.write(stripped_response + "\n")
        except Exception as e:
            print("Exception: ", e)

        # Now we basically combine the last two elements of the trajectory to get the database entry
        state_dict = ast.literal_eval(trajectory[i-1])
        # Add the bot response
        state_dict['bot_response'] = state.split("Bot response: ")[1]
        # Add the run_id
        state_dict['run_id'] = run_id
        # Add the step number
        state_dict['step'] = run_step
        # Add the timestamp
        state_dict['timestamp'] = filename
        # Flatten all nested dicts by collapsing keys
        flattened_state_dict = {f"{key}_{nested_key}": nested_value for key, value in state_dict.items() if isinstance(value, dict) for nested_key, nested_value in value.items()}
        print("To insert", state_dict)
        del flattened_state_dict['game_state_screen_state']
        # Add on the non-nested values form the original dict
        non_nested_dict = {key: value for key, value in state_dict.items() if not isinstance(value, dict)}
        flattened_state_dict.update(non_nested_dict)
        state_dict = flattened_state_dict
        # Turn all lists into strings
        for key in state_dict:
            if isinstance(state_dict[key], list):
                state_dict[key] = str(state_dict[key])

        if stripped_response is not None:
            # Insert in eval
            eval_dict = ast.literal_eval(stripped_response)
            state_dict.update(eval_dict)

        print("To insert", state_dict)
        # Insert the state
        state_table.insert(state_dict)
        # Update run_step
        run_step += 1

# Debug whether everything was added properly
print("Runs:")
for run in run_table:
    print(run)