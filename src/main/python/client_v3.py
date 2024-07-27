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
from key_queries import similar_card_choice, campfire_choice, event_choice, pathing_choice, boss_relic_choice
import string

HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 5 * 60 # 5 minutes

exception_count = 0

def create_seed():
    # Create seed like this: 5F68Z78NR2FSF
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    return ''.join(np.random.choice(list(char_string)) for _ in range(len("5F68Z78NR2FSF")))

new_run = False
def receive_messages(sock, send_message_func):
    global exception_count, new_run
    while True:
        log_filename = f"runs/{time.time()}.txt"
        raw_log_filename = f"runs_raw/{time.time()}.txt"

        with open(log_filename, "w") as log_file, open(raw_log_filename, "w") as raw_log_file:
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
                                send_message_func(sock, message, log_file, raw_log_file)
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
                        state_message = "start ironclad 10 " + create_seed()
                        new_run = True
                    '''
                    encoded_state_message = state_message.encode('utf-8')
                    sock.sendall(len(encoded_state_message).to_bytes(4, byteorder='big'))
                    sock.sendall(encoded_state_message)
                    print("Sent state message.")
                    if exception_count >= 10:
                        print("Too many exceptions. Exiting.")
                        return

last_response = "N/A (start of game)"
act_combats_completed = 0
curr_act = 1
next_choice_card = False

def send_message_func(sock, received_message, log_file, raw_log_file):
    max_action = True
    global last_response
    global act_combats_completed
    global curr_act
    global next_choice_card
    global new_run
    # Try parsing game state
    parsed_state, shared_info = parse_game_state('{"' + received_message)
    print(parsed_state)
    # If we have a battle log, extract the battle info and write to log file
    if 'battle_log' in parsed_state:
        health_change, card_counts = extract_battle_info(parsed_state['battle_log'])
        log_file.write(f'Player Health Change: {health_change}\n')
        log_file.write(f'Cards Played: {card_counts}\n')
    # Write the parsed state to log file, and the raw message to raw log file
    log_file.write(str(parsed_state) + "\n")
    raw_log_file.write(received_message + "\n")
    if "start" in parsed_state['available_commands']:
        new_run = True
        response = "start ironclad 10 " + create_seed()
        encoded_message = response.encode('utf-8')
        sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
        sock.sendall(encoded_message)
        last_response = response
        return
    parsed_state['act_combats_completed'] = act_combats_completed # This is valuable information for the bot
    if "autoplay" in parsed_state['available_commands']:
        response = "autoplay"
        act_combats_completed += 1
        # If act > curr_act, reset act_combats_completed
        if parsed_state['game_state']['act'] > curr_act:
            curr_act = parsed_state['game_state']['act']
            act_combats_completed = 0
    elif False:
        all_options = parsed_state['available_commands']
        # Randomly choose an option
        chosen_option = np.random.choice(all_options)
        # If the chosen option is "choose", randomly choose an index
        if chosen_option == "choose":
            chosen_option = "choose " + str(np.random.randint(0, len(parsed_state['game_state']['choice_list'])))
        response = chosen_option
    else:
        gpt = True
        entries = None # Hold similar entries if we run sql search on events
        # First filter out potions from the available commands if no potion slots
        choice_offset = 0
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
        elif parsed_state['game_state']['choice_list'][0] == 'gold' or parsed_state['game_state']['choice_list'][0] == 'stolen gold':
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
        # If we are currently choosing between cards, route it now to the data-driven approach
        elif next_choice_card:
            # Now we are in the card choice screen
            _, _, entries = similar_card_choice(parsed_state['game_state'], max_action) # gpt variable says whether to default to GPT when not enough data.
            next_choice_card = False
        if parsed_state['game_state']['screen_type'] == "REST" and len(parsed_state['game_state']['choice_list']) > 1:
            # Let's probabilistically make campfire decisions
            _, _, entries = campfire_choice(parsed_state['game_state'], max_action)
            #print("Response", response, gpt)
            #input("Press Enter to continue...")
        if parsed_state['game_state']['screen_type'] == "EVENT" and len(parsed_state['game_state']['choice_list']) > 1:
            # Let's probabilistically make event decisions
            _, _, entries = event_choice(parsed_state['game_state'], max_action)
            #print("Response", response, gpt)
            #input("Press Enter to continue...")
        if parsed_state['game_state']['screen_type'] == "BOSS_REWARD" and len(parsed_state['game_state']['choice_list']) > 1:
            # Let's probabilistically make boss reward decisions
            _, _, entries = boss_relic_choice(parsed_state['game_state'], max_action)
            #print("Response", response, gpt)
            #input("Press Enter to continue...")
        '''
        if parsed_state['game_state']['screen_type'] == "MAP" and len(parsed_state['game_state']['choice_list']) > 1:
            # Let's probabilistically make pathing decisions
            #_, _, entries = pathing_choice(parsed_state['game_state'], max_action)
            #print("Response", response, gpt)
            response = input("Give command...")
            gpt = False
        '''
        # Control via GPT
        #if gpt:
        #    # Just ask the user to type the command
        #    print("Parsed state", parsed_state)
        #    print("Available commands: ", parsed_state['available_commands'])
        #    response = input("Enter the command: ")
        #    gpt = False
        if gpt:
            parsed_state['last_command'] = last_response
            try:
                # Get time from log file name
                time_str = log_file.name.split('/')[-1].split('.')[0]
                response = get_text_v3(parsed_state, time_str, entries)
            except Exception as e: # We should never hit this...
                print("Exception: ", e)
                response = parsed_state['available_commands'][0]
                if response == 'choose':
                    response = 'choose 0'
            # Write response to log
            log_file.write(f'Bot response: {response}\n')
            #input("Press Enter to continue...")
    print("Response: ", response)
    print("Last response: ", last_response)
    encoded_message = response.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)
    last_response = response
    # Write response to log
    print("About to write to log: ", response)
    raw_log_file.write(f'Response: {response}\n')

def main():
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
    initial_message = "start ironclad 10 " + create_seed()
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
