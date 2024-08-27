import socket
import threading
import time
from state_parser import parse_game_state
from battle_log_parser import extract_battle_info
import numpy as np
from numpy.random import Generator, PCG64
import ast
from launch_game import start_game
import os
import signal
import select
import shutil

HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 60 # 5 minutes

exception_count = 0

'''
def create_seed():
    # Create seed like this: 5F68Z78NR2FSF
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    return ''.join(np.random.choice(list(char_string)) for _ in range(len("5F68Z78NR2FSF")))
'''

game_seed = "18AHFTJXDYBZG"

# For each run, create a random global_seed and take actions
global_seed = None

base_save_path = "/home/vsarukkai/.steam/steam/steamapps/common/SlayTheSpire/startstates/"

generator = None

def pick_start_command():
    global game_seed
    base_seed = game_seed[2:]
    i = 10
    while True: 
        game_seed = str(i).zfill(2) + base_seed
        # First visit the base save path and see how many folders exist that start with the game_seed
        valid_folders = [folder for folder in os.listdir(base_save_path) if folder.startswith(game_seed)]
        if len(valid_folders) < 50:
            break
        i += 1
    # If there are less than 20, we start a game from scratch
    if len(valid_folders) < 20:
        return "start ironclad 20 " + game_seed
    # If not, we load a game from one of the existing seeds
    else:
        attempts = 0
        while True:
            # Pick a random folder
            folder = np.random.choice(valid_folders)
            # Open the folder and check the valid floors within
            folder_path = base_save_path + folder
            valid_floors = [int(f) for f in os.listdir(folder_path)]
            if 0 in valid_floors:
                valid_floors.remove(0)
            # Sample uniformly from the valid floors
            floor = np.random.choice(valid_floors)
            # Check that the file actually exists
            if os.path.isfile(base_save_path + folder + "/" + str(floor).zfill(2) + "/saves/IRONCLAD.autosave") or attempts > 10:
                break
            attempts += 1
        # Load the floor, format like "load startstates/4ZNJ22MUNT7DX/06/saves/IRONCLAD.autosave"
        # Make sure to format the floor as a string with 2 digits
        return "load startstates/" + folder + "/" + str(floor).zfill(2) + "/saves/IRONCLAD.autosave"

def receive_messages(sock, send_message_func):
    global exception_count, global_seed
    while True:
        run_time = time.time()
        log_file_dir = "mcts_runs/" + game_seed + "/"
        # Create log file dir if it doesn't exist
        if not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)
        log_filename = f"{log_file_dir}/current.txt"
        with open(log_filename, "w") as log_file:
            last_activity_time = time.time()

            new_run = False
            while not new_run:
                try:
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
                    exception_count = 0

                except Exception as e:
                    print(f"Exception in receive_messages: {e}")
                    # Send a message with the content "state" to the server
                    # Then continue
                    exception_count += 1
                    state_message = "state"
                    '''
                    if exception_count == 5:
                        # Maybe we just need to start a new game
                        state_message = "start ironclad 10 " + game_seed
                        new_run = True
                    '''
                    encoded_state_message = state_message.encode('utf-8')
                    sock.sendall(len(encoded_state_message).to_bytes(4, byteorder='big'))
                    sock.sendall(encoded_state_message)
                    print("Sent state message.")
                    if exception_count >= 10:
                        print("Too many exceptions. Exiting.")
                        return

message_count = 0
autoplay_count = 0
start_time = time.time()
last_time = 0
total_autoplay_time = 0
last_message = "start ironclad 10 " + game_seed

def intelligent_random_choice(parsed_state, last_response):
    response = None
    if "end" in parsed_state['available_commands'] and "autoplay" not in parsed_state['available_commands']:
        # autoplay needs to load
        time.sleep(0.1)
        return "autoplay"
    if "autoplay" in parsed_state['available_commands']:
        response = "autoplay"
        return response
    if 'game_state' not in parsed_state:
        return response
    if 'potion' in parsed_state['game_state']['choice_list']: 
        # Check how many "Potion Slot" elems are in the game state potions
        potion_slots = [potion for potion in parsed_state['game_state']['potions'] if potion == 'Potion Slot']
        if len(potion_slots) == 0:
            response = "potion discard 0"
        else:
            # Find where the potion is in the choice list
            potion_index = parsed_state['game_state']['choice_list'].index('potion')
            response = "choose " + str(potion_index)
        gpt = False
    elif "open" in parsed_state['game_state']['choice_list']: # Open all chests...
        # Get the index of the "open" command
        open_index = parsed_state['game_state']['choice_list'].index('open')
        response = "choose " + str(open_index)
        gpt = False
    elif len(parsed_state['available_commands']) == 1:
        if parsed_state['available_commands'][0] != 'choose':
            response = parsed_state['available_commands'][0]
            gpt = False
        elif parsed_state['available_commands'][0] == 'choose' and len(parsed_state['game_state']['choice_list']) == 1:
            response = "choose 0"
            gpt = False
    # If we just chose to skip, then proceed to break cycles
    elif last_response == "skip" and "proceed" in parsed_state['available_commands'] and "choose" in parsed_state['available_commands']:
        response = "proceed"
        gpt = False
    # When the choice list has shop, but less than 100 gold, proceed
    elif parsed_state['game_state']['choice_list'][0] == 'shop' and parsed_state['game_state']['gold'] < 100:
        response = "proceed"
        gpt = False
    # When the choice list has a relic, choose the relic
    elif parsed_state['game_state']['choice_list'][0] == 'relic':
        response = "choose 0"
        gpt = False
    # When the choice list has gold, take the gold
    elif parsed_state['game_state']['choice_list'][0] == 'gold' or parsed_state['game_state']['choice_list'][0] == 'stolen_gold':
        response = "choose 0"
        gpt = False
    # When the choice list has gold, take the gold
    elif parsed_state['game_state']['choice_list'][0] == 'emerald_key' or parsed_state['game_state']['choice_list'][0] == 'sapphire_key':
        response = "choose 0"
        gpt = False
    # If the choice list has a card or shop, go in...but if the last command was to skip, then make sure to now proceed.
    elif last_response == "skip" and "proceed" in parsed_state['available_commands']:
        response = "proceed"
        gpt = False
    elif parsed_state['game_state']['choice_list'][0] == 'card':
        response = "choose 0"
        gpt = False
        next_choice_card = True
    #response = input("Enter your response: ")
    return response

def send_message_func(sock, received_message, log_file, raw_log_file):
    global message_count, autoplay_count, last_message, last_time, total_autoplay_time, start_time, global_seed, generator, last_response
    if last_message == "autoplay":
        total_autoplay_time += time.time() - last_time
    last_time = time.time()
    # Try parsing game state
    parsed_state, _ = parse_game_state('{"' + received_message)

    # If we have a battle log, extract the battle info and write to log file
    if 'battle_log' in parsed_state:
        health_change, card_counts = extract_battle_info(parsed_state['battle_log'])
        log_file.write(f'Player Health Change: {health_change}, ')
        log_file.write(f'Cards Played: {card_counts}\n')
    # Write the parsed state to log file, and the raw message to raw log file
    log_file.write(str(parsed_state) + "\n")

    all_options = parsed_state['available_commands']
    chosen_option = None
    if "start" in parsed_state['available_commands']:
        # First check if global_seed is None
        if global_seed is None:
            global_seed = np.random.randint(0, 1000000)
            generator = np.random.default_rng(global_seed)
        else:
            # So there should be a save folder for this seed
            # And we should copy it with a "_" + str(global_seed) suffix
            # Then create a new seed
            save_folder_name = base_save_path + game_seed
            new_save_folder_name = base_save_path + game_seed + "_" + str(global_seed)
            # Copy to create the new folder
            shutil.copytree(save_folder_name, new_save_folder_name)
            # Copy the log file as well
            log_file_name = log_file.name
            # Make sure seed is correct in this
            if not os.path.exists("mcts_runs/" + game_seed + "/"):
                os.makedirs("mcts_runs/" + game_seed + "/", exist_ok=True)
            new_log_file_name = "mcts_runs/" + game_seed + "/" + str(global_seed) + ".txt"
            shutil.copy(log_file_name, new_log_file_name)
            # Now create the new seed
            global_seed = np.random.randint(0, 1000000)
            generator = np.random.default_rng(global_seed)
        # Delete the old save folder regardless if it exists
        save_folder_name = base_save_path + game_seed
        shutil.rmtree(save_folder_name, ignore_errors=True)
        # Wipe anything in the log file if it exists
        log_file.seek(0)
        log_file.truncate()
        # Start game
        chosen_option = pick_start_command() #"start ironclad 10 " + game_seed
    if chosen_option is None:
        chosen_option = intelligent_random_choice(parsed_state, last_message) # Do the default rules for simple decisions
    if chosen_option is None:
        # Randomly choose an option
        if generator is not None:
            chosen_option = generator.choice(all_options)
        else:
            chosen_option = None
        # If the chosen option is "choose", randomly choose an index
        if chosen_option == "choose":
            chosen_option = "choose " + str(generator.integers(0, len(parsed_state['game_state']['choice_list'])))
    response = chosen_option
    # If the choice is "choose x", replace x with the actual choice string
    if response.startswith("choose"):
        choice_index = int(response.split(" ")[1])
        response = "choose " + parsed_state['game_state']['choice_list'][choice_index]
    message_count += 1
    encoded_message = response.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)
    last_message = response
    print(f"Sent: {response}")
    # Print message rate
    if message_count > 3:
        print(f"Message rate: {(message_count - autoplay_count - 3) / (time.time() - start_time - total_autoplay_time + 0.001)}")
        print(f"Autoplay rate: {autoplay_count / (total_autoplay_time + 0.001)}")
    else:
        start_time = time.time()

    # Log this
    log_file.write(f'Response: {response}\n')
    # Flush
    log_file.flush()

def main():
    process_1, process_2 = start_game()
    
    # Wait 20 seconds for the game to start
    time.sleep(20)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST_IP, PORT))
        print("Connected to the server.")
    except Exception as e:
        print(f"Exception in connecting to the server: {e}")
        return

    # Send the initial message
    initial_message = "state" #"start ironclad 10"
    encoded_message = initial_message.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)
    print("Initial message sent.")

    # Start the receive_messages function
    receive_messages(sock, send_message_func)

    sock.close()
    print("Connection closed.")

    # Kill the game processes
    os.kill(process_1.pid, signal.SIGTERM)
    os.kill(process_2.pid, signal.SIGTERM)

    # Wait one second for death
    time.sleep(1)

if __name__ == "__main__":
    main()