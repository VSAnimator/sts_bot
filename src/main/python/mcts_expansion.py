from seed_mcts import intelligent_random_choice
import socket
import threading
import time
from state_parser import parse_game_state
from battle_log_parser import extract_battle_info
import numpy as np
from openai_helpers import value_decision
import ast
from launch_game import start_game
import os
import signal
import select
from act1_queries import event_query, card_choice_query, campfire_query, smithing_query, map_query
import string
import random
from datetime import datetime, timedelta
from numpy.random import Generator, PCG64
import shutil
from pprint import pprint
import copy
import sys
import dataset

# Generic MCTS agent
# Can be used with different decision and lookahead policies

game_seed = None
HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 2 * 60 # 2 minutes
last_response = "N/A (start of game)"
last_lookahead_response = "N/A (start of game)"
generator = np.random.default_rng(0)
save_dir = "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources/startstates/"

# The policy used for decisions by default
def decision_policy(parsed_state, mcts_state, mcts_file):
    global game_seed
    print("Parsed state", parsed_state)
    pprint(mcts_state.leaf_states)
    # Copy the mcts file
    to_copy = mcts_file.name[:-4] + "_" + str(parsed_state['game_state']['floor']) + ".txt"
    # Copy mcts_file to to_copy
    shutil.copy(mcts_file.name, to_copy)
    # Clear mcts_file
    mcts_file.seek(0)
    mcts_file.truncate()
    # Return a command to load the state for the next floor
    curr_floor = parsed_state['game_state']['floor']

    # Save the leaf states to a file
    with open(f"mcts_agent_runs/{game_seed}/leaf_states_{curr_floor}.txt", "w") as f:
        f.write(str(mcts_state.leaf_states))

    # Find the first number without a leaf state file
    for i in range(curr_floor+1, 45):
        # Check if the leaf state file exists
        if not os.path.exists(f"mcts_agent_runs/{game_seed}/leaf_states_{i}.txt"):
            return "load startstates/" + game_seed + "_gt/" + str(i).zfill(2) + "/saves/IRONCLAD.autosave"
        
    return None
    #return "load startstates/" + game_seed + "_gt/" + str(curr_floor + 1).zfill(2) + "/saves/IRONCLAD.autosave"

def get_all_options(parsed_state):
    all_options = copy.deepcopy(parsed_state['available_commands'])
    choice_list = copy.deepcopy(parsed_state['game_state']['choice_list'])
    # If "choose" is one of the options, then "roll" the other options into the choice list
    if "choose" in all_options:
        all_options = [command for command in all_options if command != "choose"]
        # For all commands in choice_list, append the word "choose " to the front
        for i in range(len(choice_list)):
            choice_list[i] = "choose " + choice_list[i]
        all_options.extend(choice_list)
    return all_options

def random_action(parsed_state, chosen_options = []):
    #print("Taking random action")
    global generator
    # Randomly choose an option
    all_options = get_all_options(parsed_state)
    # Remove chosen actions
    print("Already chosen:", chosen_options)
    filtered_options = [action for action in all_options if action not in chosen_options]
    if len(filtered_options) > 0:
        all_options = filtered_options
    print("Options", all_options)
    if generator is not None:
        chosen_option = generator.choice(all_options)
    else:
        chosen_option = None
    print("Chosen:", chosen_option)
    return chosen_option

# MCTS parameters
mcts_depth = 4
mcts_samples = 4
last_mcts_floor = 0

# Run inference
class MctsState:
    in_mcts = False
    curr_floor = 0 # String mapping to path of state desired
    samples_taken = 0
    curr_command = ""
    path_commands = ""
    leaf_states = {} # Dict mapping from choice taken to state reached

mcts_state = MctsState()

db = dataset.connect('sqlite:///labeling.db')

state_table = db['states']

def map_query(parsed_state):
    # Query the database for the path taken
    query = f"SELECT * FROM states WHERE game_state_floor={parsed_state['game_state']['floor']} AND timestamp='{game_seed}' and game_state_screen_type='MAP'"
    result = db.query(query)
    states = list(result)
    return states[0]['bot_response']

# The policy used for MCTS lookaheads
def lookahead_policy(parsed_state):
    global last_lookahead_response, mcts_state
    chosen_option = intelligent_random_choice(parsed_state, last_lookahead_response)
    print("Intelligent random choice:", chosen_option)
    random = False
    if chosen_option is None:
        random = True
        if mcts_state.curr_command == "":
            chosen_option = random_action(parsed_state, list(mcts_state.leaf_states.keys()))
        else:
            # Handle pathing decisions separately
            if parsed_state['game_state']['screen_type'] == "MAP":
                # Query the database for the path taken
                chosen_option = map_query(parsed_state)
                # Check to make sure the chosen option is valid
                all_options = get_all_options(parsed_state)
                if chosen_option not in all_options:
                    print("INVALID MAP CHOICE")
                    #input("Continue?")
                    chosen_option = random_action(parsed_state)
            else:
                chosen_option = random_action(parsed_state)
    return chosen_option, random

# Next command to issue for the MCTS search
# Could be a reset to the starting state to start a new tree, proceeding in tree search, or 
def next_mcts_command(sock, received_message, log_file, mcts_file):
    global mcts_state, mcts_depth, mcts_samples, lookahead_policy, game_seed, last_response, last_lookahead_response, last_mcts_floor
    try:
        parsed_state, _ = parse_game_state('{"' + received_message)
        if not mcts_state.in_mcts:
            print("Path commands", mcts_state.path_commands)
            #input("Please look")
            next_path_command = None
            # By default we run intelligent random choice
            try:
                next_command = intelligent_random_choice(parsed_state, last_response)
            except:
                next_command = None
            # When that returns none, start mcts
            if next_command is None:
                if len(mcts_state.path_commands) > 2:
                    next_path_command = mcts_state.path_commands.split(",")[0]
                    mcts_state.path_commands = mcts_state.path_commands[len(next_path_command) + 1:]
                if 'game_state' not in parsed_state:
                    # Game is over
                    return "Game over"
                if parsed_state['game_state']['floor'] > last_mcts_floor:
                    last_mcts_floor = parsed_state['game_state']['floor']
                    mcts_state.in_mcts = True
                    mcts_state.path_commands = ""
                    mcts_state.curr_floor = parsed_state['game_state']['floor']
                else:
                    # Take a random action
                    all_options = get_all_options(parsed_state)
                    print("All options", all_options)
                    print("Next_path_command", next_path_command)
                    print("Path commands", mcts_state.path_commands)
                    #input("Need to look here")
                    if next_path_command is not None and next_path_command in all_options:
                        next_command = next_path_command
                    else:
                        next_command = random_action(parsed_state)
        if mcts_state.in_mcts:
            # Figure out if re-loading start state for new branch, running lookahead policy, or making decision
            if mcts_state.samples_taken < mcts_samples:
                end_rollout = False
                if 'victory' in parsed_state['game_state']['screen_state']:
                    end_rollout = True
                if parsed_state['game_state']['floor'] < mcts_state.curr_floor + mcts_depth and not end_rollout:
                    # Keep running lookahead policy
                    next_command, random = lookahead_policy(parsed_state)
                    if mcts_state.curr_command == "" and random:
                        mcts_state.curr_command = next_command
                    last_lookahead_response = next_command
                    if parsed_state['game_state']['floor'] == mcts_state.curr_floor and random:
                        mcts_state.path_commands = mcts_state.path_commands + next_command + ","
                else:
                    # We need to add the end state to leaf_states
                    if mcts_state.curr_command not in mcts_state.leaf_states:
                        mcts_state.leaf_states[mcts_state.curr_command] = []
                    parsed_state['path_commands'] = mcts_state.path_commands
                    mcts_state.leaf_states[mcts_state.curr_command].append(parsed_state)
                    mcts_state.samples_taken += 1
                    mcts_state.curr_command = ""
                    mcts_state.path_commands = ""
                    next_command = "load startstates/" + game_seed + "_gt/" + str(mcts_state.curr_floor).zfill(2) + "/saves/IRONCLAD.autosave"
                    last_lookahead_response = last_response
            else:
                # Time to make a decision
                # First roll forward to decision
                next_command = intelligent_random_choice(parsed_state, last_response)
                if next_command is None:
                    #input("Time for decision")
                    next_command = decision_policy(parsed_state, mcts_state, mcts_file)
                    if next_command is None:
                        return "Game over"
                    #input("Decisiont made")
                    print("Decision made:", next_command)
                    print("Leaf states", list(mcts_state.leaf_states.keys()))
                    #input("Key issue")
                    # Make sure the path taken by the chosen node is available
                    if next_command in mcts_state.leaf_states:
                        print(mcts_state.leaf_states[next_command])
                        print(mcts_state.leaf_states[next_command][0])
                        mcts_state.path_commands = mcts_state.leaf_states[next_command][0]['path_commands']
                        # Remove the first command
                        mcts_state.path_commands = mcts_state.path_commands[len(next_command) + 1:]
                    # Note that mcts is over now for the step
                    mcts_state.in_mcts = False
                    mcts_state.leaf_states = {}
                    mcts_state.samples_taken = 0
                    mcts_state.curr_command = ""
    
        # Now replace the number with the text for the command
        '''
        if "choose" in next_command:
            choice_index = int(next_command.split("choose ")[1])
            next_command = "choose " + parsed_state['game_state']['choice_list'][choice_index]
        '''
        # Make sure to add this decision to the log
        if not mcts_state.in_mcts:
            log_file.write(str(parsed_state) + "\n")
            log_file.write(f'Bot response: {next_command}\n')
            log_file.flush()
            last_response = next_command
        else:
            mcts_file.write(str(parsed_state) + "\n")
            mcts_file.write(f'Bot response: {next_command}\n')
            mcts_file.flush()
        print("Response:", next_command)
        # Run the command whatever it is
        encoded_message = next_command.encode('utf-8')
        sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
        sock.sendall(encoded_message)

    except Exception as e:
        print(f"Exception in next_mcts_command: {e}")
        return "Game over"

def create_seed():
    # Create seed like this: 5F68Z78NR2FSF
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    return '13BHFTJXDYBZG'
    #return ''.join(np.random.choice(list(char_string)) for _ in range(len("5F68Z78NR2FSF")))

def receive_messages(sock, send_message_func):
    global exception_count, game_seed
    run_time = time.time()
    log_file_dir = "mcts_agent_runs/" + game_seed + "/"
    # Create log file dir if it doesn't exist
    if not os.path.exists(log_file_dir):
        os.makedirs(log_file_dir, exist_ok=True)
    log_filename = f"{log_file_dir}/current.txt"
    mcts_filename = f"{log_file_dir}/mcts.txt"
    with open(log_filename, "w") as log_file:
        with open(mcts_filename, "w") as mcts_file:
            last_activity_time = time.time()

            new_run = False
            while True:
                current_time = time.time()

                # Check if we have exceeded the timeout threshold
                if current_time - last_activity_time > TIMEOUT_THRESHOLD:
                    print("No activity for 5 minutes. Exiting.")
                    return

                # Use select to handle socket operations with a timeout
                read_sockets, _, _ = select.select([sock], [], [], 1.0)

                if read_sockets:
                    msg_length = sock.recv(4)
                    if msg_length:
                        msg_length = int.from_bytes(msg_length, byteorder='big')
                        message = sock.recv(msg_length).decode('utf-8')
                        if message:
                            #print(message)
                            temp = send_message_func(sock, message, log_file, mcts_file)
                            last_activity_time = current_time  # Update last activity time
                            if temp is not None:
                                return
                        else:
                            print("Empty message received. Exiting.")
                            return
                    else:
                        print("No message length received. Exiting.")
                        return

def main():
    global game_seed
    process_1, process_2 = start_game()
    
    # Wait 20 seconds for the game to start
    time.sleep(40)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST_IP, PORT))
        print("Connected to the server.")
    except Exception as e:
        print(f"Exception in connecting to the server: {e}")
        return

    # Send the initial message
    game_seed = sys.argv[1]

    # Copy valid_folders_archive/seed to startstates/seed_gt
    shutil.copytree("valid_folders_archive/" + game_seed, save_dir + game_seed + "_gt", dirs_exist_ok=True)

    # Find the first number without a leaf state file
    for i in range(1, 45):
        # Check if the leaf state file exists
        if not os.path.exists(f"mcts_agent_runs/{game_seed}/leaf_states_{i}.txt"):
            if i == 1:
                initial_message = "start ironclad 10 " + game_seed
            else:
                initial_message = "load startstates/" + game_seed + "_gt/" + str(i+1).zfill(2) + "/saves/IRONCLAD.autosave"
            break
        
    encoded_message = initial_message.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)
    print("Initial message sent.")

    # Start the receive_messages function
    receive_messages(sock, next_mcts_command)

    sock.close()
    print("Connection closed.")

    # Kill the game processes
    os.kill(process_1.pid, signal.SIGTERM)
    os.kill(process_2.pid, signal.SIGTERM)

    # Wait one second for death
    time.sleep(1)

if __name__ == "__main__":
    main()