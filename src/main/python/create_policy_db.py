import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
from os import listdir
from os.path import isfile, join

db = dataset.connect('sqlite:///policy.db')

state_table = db['states']

# Insert all runs in "runs" folder
# Get list of filenames from "runs/"
folder_path = "valid_folders_archive/policy_runs/"
filenames = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]

valid_count = 0
win_count = 0
floor_reached = []
for elem in filenames:
    if "test" in elem:
        continue
    print("Processing: ", elem)
    with open(folder_path + elem, "r") as file:
        trajectory_file = file.read()
    filename = elem.split("_")[0]
    # Split into a list line by line
    trajectory = trajectory_file.split("\n")

    if len(trajectory) < 2:
        continue

    trajectory = [elem for elem in trajectory if '\'start\'' not in elem]

    run_step = 0
    # Now loop through the trajectory and analyze each decision
    for i in range(len(trajectory) - 1):
        state = trajectory[i]
        # Check if its a bot action
        if "Policy response: " not in state:
            continue

        # Now we basically combine the last two elements of the trajectory to get the database entry
        state_dict = ast.literal_eval(trajectory[i-1][7:])

        # Add the bot response
        state_dict['policy_response'] = state[17:]
        # Add the step number
        state_dict['step'] = run_step
        # Add the timestamp
        state_dict['timestamp'] = filename
        # Pull out next_node_info
        if 'next_node_info' in state_dict['game_state']['screen_state']:
            state_dict['next_node_info'] = state_dict['game_state']['screen_state']['next_node_info']
        if 'next_nodes' in state_dict['game_state']['screen_state']:
            state_dict['next_nodes'] = state_dict['game_state']['screen_state']['next_nodes']
        if 'event_id' in state_dict['game_state']['screen_state']:
            state_dict['event_id'] = state_dict['game_state']['screen_state']['event_id']
        # Flatten all nested dicts by collapsing keys
        flattened_state_dict = {f"{key}_{nested_key}": nested_value for key, value in state_dict.items() if isinstance(value, dict) for nested_key, nested_value in value.items()}
        del flattened_state_dict['game_state_screen_state']
        # Add on the non-nested values form the original dict
        non_nested_dict = {key: value for key, value in state_dict.items() if not isinstance(value, dict)}
        flattened_state_dict.update(non_nested_dict)
        state_dict = flattened_state_dict
        # Turn all lists into strings
        for key in state_dict:
            if isinstance(state_dict[key], list):
                state_dict[key] = json.dumps(state_dict[key])

        print("To insert", state_dict)
        # Insert the state
        state_table.insert(state_dict)
        # Update run_step
        run_step += 1

print("Valid count", valid_count)
print("Win count", win_count)
print("Avg floor reached", np.mean(floor_reached))
print("Floor reached", floor_reached)