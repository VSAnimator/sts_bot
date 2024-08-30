import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
from os import listdir
from os.path import isfile, join

db = dataset.connect('sqlite:///labeling.db')

# Create tables for runs and for individual states
run_table = db['runs']
state_table = db['states']

# Insert all runs in "runs" folder
# Get list of filenames from "runs/"
folder_path = "valid_folders_archive/"
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

    try:
        final_state = ast.literal_eval(trajectory[-2])
    except:
        print("Error parsing final state")
        continue
    if 'game_state' in final_state and 'screen_type' in final_state['game_state'] and final_state['game_state']['screen_type'] == 'GAME_OVER' and final_state['game_state']['ascension_level'] == 10:
        print("Valid run: ", filename)
        valid_count += 1
        if final_state['game_state']['screen_state']['victory']:
            win_count += 1
        floor_reached.append(final_state['game_state']['floor'])
    else:
        continue

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
    # Skip if not ascension 10
    if final_state_info['ascension_level'] != 10:
        continue
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

        # Now we basically combine the last two elements of the trajectory to get the database entry
        '''
        if "\"Philosopher's Stone\"" in trajectory[i-1]:
            # We need to fix this for parsing: double quotes to single quotes, escape the apostrophe
            #trajectory[i-1] = trajectory[i-1].replace("\"Philosopher's Stone\"", "\'Philosopher\\\'s Stone\'")
            state_dict = ast.literal_eval(trajectory[i-1])
            print("State dict", state_dict)
            print("Trajectory", trajectory[i-1])
            print("Relics", state_dict['game_state']['relics'])
            input("Continue?")
        '''
        state_dict = ast.literal_eval(trajectory[i-1])
    
        #print("State dict", state_dict)
        # We want to collapse the choice_list into available_commands
        # If "choose" is one of the options, then "roll" the other options into the choice list
        if "choose" in state_dict['available_commands']:
            # For all commands in choice_list, append the word "choose " to the front
            for i in range(len(state_dict['game_state']['choice_list'])):
                state_dict['game_state']['choice_list'][i] = "choose " + state_dict['game_state']['choice_list'][i]
        # For sozu, we need to remove options containing "potion" from the list of options when in the shop
        if "sozu" in state_dict['game_state']['relics'] and state_dict['game_state']['screen_type'] == "SHOP_SCREEN":
            state_dict['game_state']['choice_list'] = [command for command in state_dict['game_state']['choice_list'] if "potion" not in command]
        state_dict['game_state']['choice_list'].extend(state_dict['available_commands'])
        if "choose" in state_dict['game_state']['choice_list']:
            state_dict['game_state']['choice_list'].remove("choose")

        # Add the bot response
        state_dict['bot_response'] = state.split("Bot response: ")[1]
        # Add the run_id
        state_dict['run_id'] = run_id
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
        print("To insert", state_dict)
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

# Now loop through valid_folders_raw, and modify rows to add in the current_node and map info
folder_path = "valid_folders_raw_archive/"
filenames = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]

for elem in filenames:
    curr_act = 0
    curr_floor = -1
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
        if "Response: " not in state:
            continue

        trajectory[i-1] = trajectory[i-1].replace("true", "True")
        trajectory[i-1] = trajectory[i-1].replace("false", "False")
        state_dict = ast.literal_eval("{\"" + trajectory[i-1])
        #print("State dict", state_dict)
    
        # Find the map and current node
        if 'map' in state_dict['game_state']:
            state_dict['map'] = json.dumps(state_dict['game_state']['map'])
        if 'current_node' in state_dict['game_state']['screen_state']:
            state_dict['current_node'] = json.dumps(state_dict['game_state']['screen_state']['current_node'])
        
        if 'act' in state_dict['game_state'] and state_dict['game_state']['act'] != curr_act:
            curr_act = state_dict['game_state']['act']
            result = state_table.update({'timestamp': filename, 'game_state_act': state_dict['game_state']['act'], 'map': state_dict['map']}, ['timestamp', 'game_state_act'])
            print("Updated map for act: ", curr_act)
        if 'current_node' in state_dict and state_dict['game_state']['floor'] != curr_floor:
            result = state_table.update({'timestamp': filename, 'game_state_floor': state_dict['game_state']['floor'], 'current_node': state_dict['current_node']}, ['timestamp', 'game_state_floor'])
            curr_floor = state_dict['game_state']['floor']
            print("Updated current node for floor: ", curr_floor)

# Debug whether everything was added properly
print("Runs:")
count = 0
for run in run_table:
    print(run)
    count += 1

print("Total count", count)

print("Valid count", valid_count)
print("Win count", win_count)
print("Avg floor reached", np.mean(floor_reached))
print("Floor reached", floor_reached)