import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
from os import listdir
from os.path import isfile, join
from openai_helpers import get_text_v3

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

    run_step = 0
    # Create a log file to store everything
    write_file = open(folder_path + "policy_runs/" + filename + "_policy.txt", "w")
    # Now loop through the trajectory and analyze each decision
    for i in range(len(trajectory) - 1):
        state = trajectory[i]
        # Check if its a bot action
        if "Bot response: " not in state:
            continue

        state_dict = ast.literal_eval(trajectory[i-1])
    
        # Run the policy function without similar states or joe advice
        policy_response = get_text_v3(state_dict, filename + "_policy", None, human_test=False, use_joe_advice=False)

        # Write the policy response to the log file
        write_file.write(f"Step {run_step}\n")
        write_file.write(f"State: {state_dict}\n")
        write_file.write(f"Policy response: {policy_response}\n\n")
        write_file.flush()

        # Update run_step
        run_step += 1
