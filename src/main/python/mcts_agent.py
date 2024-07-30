from seed_mcts import intelligent_random_choice
import socket
import threading
import time
from state_parser import parse_game_state
from battle_log_parser import extract_battle_info
import numpy as np
from openai_helpers import get_text, get_text_v2, get_text_v3
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

# Generic MCTS agent
# Can be used with different decision and lookahead policies

game_seed = None
HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 5 * 60 # 5 minutes
last_response = "N/A (start of game)"
last_lookahead_response = "N/A (start of game)"
generator = np.random.default_rng(0)

# The policy used for decisions by default
def decision_policy(parsed_state, mcts_state):
    print("Parsed state", parsed_state)
    print("Mcts state", mcts_state.leaf_states)
    return input("What command do we wanna take?")

def random_action(parsed_state):
    print("Taking random action")
    global generator
    # Randomly choose an option
    all_options = parsed_state['available_commands']
    print("Options", all_options)
    if generator is not None:
        chosen_option = generator.choice(all_options)
    else:
        chosen_option = None
    # If the chosen option is "choose", randomly choose an index
    if chosen_option == "choose":
        chosen_option = "choose " + str(generator.integers(0, len(parsed_state['game_state']['choice_list'])))
    print("Chosen", chosen_option)
    return chosen_option

# The policy used for MCTS lookaheads
def lookahead_policy(parsed_state):
    global last_lookahead_response
    chosen_option = intelligent_random_choice(parsed_state, last_lookahead_response)
    print("Intelligent random choice:", chosen_option)
    random = False
    if chosen_option is None:
        random = True
        chosen_option = random_action(parsed_state)
    return chosen_option, random

# MCTS parameters
mcts_depth = 2
mcts_samples = 3
last_mcts_floor = 0

# Run inference
class MctsState:
    in_mcts = False
    curr_floor = 0 # String mapping to path of state desired
    samples_taken = 0
    curr_command = ""
    leaf_states = {} # Dict mapping from choice taken to state reached

mcts_state = MctsState()

# Next command to issue for the MCTS search
# Could be a reset to the starting state to start a new tree, proceeding in tree search, or 
def next_mcts_command(sock, received_message, log_file, raw_log_file):
    global mcts_state, mcts_depth, mcts_samples, lookahead_policy, game_seed, last_response, last_lookahead_response, last_mcts_floor
    parsed_state, _ = parse_game_state('{"' + received_message)
    if not mcts_state.in_mcts:
        # By default we run intelligent random choice
        next_command = intelligent_random_choice(parsed_state, last_response)
        # When that returns none, start mcts
        if next_command is None:
            if parsed_state['game_state']['floor'] > last_mcts_floor:
                last_mcts_floor = parsed_state['game_state']['floor']
                mcts_state.in_mcts = True
                mcts_state.curr_floor = parsed_state['game_state']['floor']
            else:
                # Take a random action
                next_command = random_action(parsed_state)
    if mcts_state.in_mcts:
        # Figure out if re-loading start state for new branch, running lookahead policy, or making decision
        if mcts_state.samples_taken < mcts_samples:
            if parsed_state['game_state']['floor'] < mcts_state.curr_floor + mcts_depth:
                # Keep running lookahead policy
                next_command, random = lookahead_policy(parsed_state)
                if mcts_state.curr_command == "" and random:
                    mcts_state.curr_command = next_command
                last_lookahead_response = next_command
            else:
                # We need to add the end state to leaf_states
                if mcts_state.curr_command not in mcts_state.leaf_states:
                    mcts_state.leaf_states[mcts_state.curr_command] = []
                mcts_state.leaf_states[mcts_state.curr_command].append(parsed_state)
                mcts_state.samples_taken += 1
                mcts_state.curr_command = ""
                next_command = "load startstates/" + game_seed + "/" + str(mcts_state.curr_floor).zfill(2) + "/saves/IRONCLAD.autosave"
                last_lookahead_response = last_response
        else:
            # Time to make a decision
            # First roll forward to decision
            next_command = intelligent_random_choice(parsed_state, last_response)
            if next_command is None:
                next_command = decision_policy(parsed_state, mcts_state)
                # Note that mcts is over now for the step
                mcts_state.in_mcts = False
                mcts_state.leaf_states = {}
                mcts_state.samples_taken = 0
                mcts_state.curr_command = ""
    # Make sure to add this decision to the log
    if not mcts_state.in_mcts:
        log_file.write(str(parsed_state) + "\n")
        log_file.write(f'Bot response: {next_command}\n')
        last_response = next_command
    print("Response:", next_command)
    # Run the command whatever it is
    encoded_message = next_command.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)

def create_seed():
    # Create seed like this: 5F68Z78NR2FSF
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    return '18BHFTJXDYBZG'
    #return ''.join(np.random.choice(list(char_string)) for _ in range(len("5F68Z78NR2FSF")))

def receive_messages(sock, send_message_func):
    global exception_count, game_seed
    run_time = time.time()
    log_file_dir = "mcts_agent_runs/" + game_seed + "/"
    # Create log file dir if it doesn't exist
    if not os.path.exists(log_file_dir):
        os.makedirs(log_file_dir, exist_ok=True)
    log_filename = f"{log_file_dir}/current.txt"
    with open(log_filename, "w") as log_file:
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
                        print(message)
                        send_message_func(sock, message, log_file, None)
                        last_activity_time = current_time  # Update last activity time
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
    game_seed = create_seed()
    initial_message = "start ironclad 10 " + create_seed()
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