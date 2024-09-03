import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
from os import listdir
from os.path import isfile, join
from openai_helpers import get_best_state

db = dataset.connect('sqlite:///value_mcts.db')

state_table = db['states']

# Insert all runs in "runs" folder
# Get list of filenames from "runs/"
folder_path = "/Users/sarukkai/Downloads/mcts_agent_runs_v1/"
filenames = [f for f in listdir(folder_path) if not isfile(join(folder_path, f))]

'''
for elem in filenames:
    print("Processing: ", elem)
    with open(folder_path + elem, "r") as file:
        trajectory_file = file.read()
    x = ast.literal_eval(trajectory_file)
    for key, val in x.items():
        print(key)
        print(len(val))
'''

def get_mcts_seed_floor(seed, floor):
    #elem_path = "/Users/sarukkai/Downloads/mcts_agent_runs_v1/" + seed + "/leaf_states_" + str(floor) + ".txt"
    elem_path = "./mcts_agent_runs/" + seed + "/leaf_states_" + str(floor) + ".txt"
    # Check if file exists
    if not os.path.exists(elem_path):
        return {}
    with open(elem_path, "r") as file:
        trajectory_file = file.read()
    x = ast.literal_eval(trajectory_file)
    return x

# Open log file
log_file = open("value_decisions.txt", "w")

for elem in ["18G9QFD18M8Y2"]:
    for floor in range(1, 51):
        try:
            #print("Processing: ", elem)
            seed = elem.split("_")[0]
            x = get_mcts_seed_floor(seed, floor)
            #print(x)
            if len(x) == 0:
                continue
            if len(x) > 5:
                # Skip if too many choices
                continue
            print("Seed: ", seed)
            print("Floor: ", floor)
            best_states = {}
            for key, val in x.items():
                print(key)
                # For each state in prompt_states, keep deck, relics, floor, current_hp, max_hp, potions
                val = [{k: v for k, v in state['game_state'].items() if k in ['deck', 'relics', 'floor', 'act_boss', 'current_hp', 'max_hp', 'potions']} for state in val]
            #    print(len(val))
                # If 1 element, return that element
                if len(val) == 1:
                    best_states[key] = val[0]
                    continue
                best_states[key] = get_best_state(val, elem + "_" + str(floor))
            best_state = get_best_state(best_states.values(), elem + "_" + str(floor))
            # Get key for best state
            best_state_key = list(best_states.keys())[list(best_states.values()).index(best_state)]
            print("Best state: ", best_state)
            print("Best state key: ", best_state_key)
            
            # Write to log file
            log_file.write(f"Seed: {seed}\n")
            log_file.write(f"Floor: {floor}\n")
            log_file.write(f"Best state: {best_state}\n")
            log_file.write(f"Best state key: {best_state_key}\n\n")
            log_file.write(f"Best states dict: {best_states}\n\n")
            log_file.flush()
        except Exception as e:
            print("Error: ", e)
            continue
