import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
import glob

db = dataset.connect('sqlite:///mcts.db')

# Create tables for runs and for individual states
run_table = db['runs']
state_table = db['states']

# Want a table to store location visits
location_table = db['locations']

# Insert all runs in "runs" folder
# Get list of filenames from "runs/"
base_path = "mcts_runs/28BHFTJXDYBZG/"
filenames = list(filter(os.path.isfile, glob.glob(base_path + "*"))) # Sort by time to handle branching
filenames.sort(key = os.path.getctime)

# How to join parts of the tree search?

valid_count = 0
win_count = 0
floor_reached = []
for elem in filenames:
    if "test" in elem:
        continue
    print("Processing: ", elem)
    filename = elem.split(".txt")[0]
    parent_file = None
    with open(filename + ".txt", "r") as file:
        trajectory_file = file.read()
    # Split into a list line by line
    trajectory = trajectory_file.split("\n")

    trajectory = trajectory[:-1]

    if len(trajectory) < 2:
        continue

    trajectory = [elem for elem in trajectory if '\'start\'' not in elem]

    win = False

    try:
        final_state = ast.literal_eval(trajectory[-2])
    except:
        print("Error parsing final state")
        continue
    if 'game_state' in final_state and 'screen_type' in final_state['game_state'] and final_state['game_state']['screen_type'] == 'GAME_OVER' and final_state['game_state']['ascension_level'] == 10:
        print("Valid run: ", filename)
        valid_count += 1
        if final_state['game_state']['floor'] > 16: #['screen_state']['victory']:
            win_count += 1
            win = True
        floor_reached.append(final_state['game_state']['floor'])

        # Parse this type of string: Response: load startstates/18BHFTJXDYBZG_643019/06/saves/IRONCLAD.autosave
        #print(trajectory[0])
        if "load " in trajectory[0]:
            continue # For now no branching?
            parent_file = trajectory[0].split("load ")[1]
            parent_file = parent_file.split("/")[1].split("_")[1]
            # Now increment visit counts and potentially win count for all parent file states
            # Write query to increment location table column by filter
            query = f"UPDATE locations SET count = count + 1 WHERE timestamp = \"{base_path + parent_file}\""
            db.query(query)
            if win:
                query = f"UPDATE locations SET win = win + 1 WHERE timestamp = \"{base_path + parent_file}\""
                db.query(query)
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
    for i in range(1, len(trajectory) - 1):
        state = trajectory[i]
        # Check if its a bot action
        if "Response: " not in state:
            continue

        # Now we basically combine the last two elements of the trajectory to get the database entry
        try:
            state_dict = ast.literal_eval(trajectory[i-1])
        except:
            print("Error parsing state")
            print(trajectory[i-1])
            print(trajectory[i])
            exit()
            continue

        if state_dict['game_state']['act'] > 1:
            break

        # Now also add the location to the location table
        if 'game_state' in state_dict and 'screen_state' in state_dict['game_state']:
            if 'current_node' in state_dict['game_state']['screen_state']:
                node = state_dict['game_state']['screen_state']['current_node']
                print(node['x'], node['y'])
                if (node['x'] == 0 and node['y'] == 0):
                    print("uhoh")
                    exit()
                location_dict = {
                    "location": str((node['y'], node['x'])),
                    "run_id": run_id,
                    "timestamp": filename,
                    "win": win,
                    "count": 1
                }
                location_table.insert(location_dict)

        # Add the bot response
        state_dict['bot_response'] = state.split("Response: ")[1]
        # Add the run_id
        state_dict['run_id'] = run_id
        # Add the step number
        state_dict['step'] = run_step
        # Add the timestamp
        state_dict['timestamp'] = filename
        # Flatten all nested dicts by collapsing keys
        flattened_state_dict = {f"{key}_{nested_key}": nested_value for key, value in state_dict.items() if isinstance(value, dict) for nested_key, nested_value in value.items()}
        #print("To insert", state_dict)
        del flattened_state_dict['game_state_screen_state']
        # Add on the non-nested values form the original dict
        non_nested_dict = {key: value for key, value in state_dict.items() if not isinstance(value, dict)}
        flattened_state_dict.update(non_nested_dict)
        state_dict = flattened_state_dict
        # Turn all lists into strings
        for key in state_dict:
            if isinstance(state_dict[key], list):
                state_dict[key] = str(state_dict[key])

        #print("To insert", state_dict)
        # Insert the state
        state_table.insert(state_dict)
        # Update run_step
        run_step += 1

# Debug whether everything was added properly
print("Runs:")
count = 0
for run in run_table:
    #print(run)
    count += 1

print("Total count", count)

print("Valid count", valid_count)
print("Win count", win_count)
print("Avg floor reached", np.mean(floor_reached))
print("Floor reached", floor_reached)

# List tables present
print(db.tables)

# Query location table to return average win rate by location
query = "SELECT location, SUM(win)*1.0/SUM(count), SUM(WIN), SUM(COUNT) FROM locations GROUP BY location"
results = db.query(query)
for result in results:
    print(result)