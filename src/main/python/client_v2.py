import socket
import threading
from state_parser import parse_game_state
from battle_log_parser import extract_battle_info
import numpy as np
from openai_helpers import get_text, get_text_v2
import time
import ast

HOST_IP = "127.0.0.1"
PORT = 8080

def receive_messages(sock, send_message_func):
    # Create a file to log the messages
    # Make a unique name reflecting the timestamp
    #log_file = open("runs/log.txt", "w")
    log_file = open("runs/" + str(time.time()) + ".txt", "w")
    raw_log_file = open("runs_raw/" + str(time.time()) + ".txt", "w")
    while True:
        msg_length = sock.recv(4)
        if not msg_length:
            break

        msg_length = int.from_bytes(msg_length, byteorder='big')
        message = sock.recv(msg_length).decode('utf-8')
        if message:
            print(message)
            send_message_func(sock, message, log_file, raw_log_file)
        else:
            break

last_response = "N/A (start of game)"
act_combats_completed = 0
curr_act = 1

def send_message_func(sock, received_message, log_file, raw_log_file):
    global last_response
    global act_combats_completed
    global curr_act
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
        # Control via GPT
        if gpt:
            parsed_state['last_command'] = last_response
            try:
                # Get time from log file name
                time_str = log_file.name.split('/')[-1].split('.')[0]
                response = get_text_v2(parsed_state, time_str)
            except Exception as e:
                print("Exception: ", e)
                response = parsed_state['available_commands'][0]
                if response == 'choose':
                    response = 'choose 0'
            # Write response to log
            log_file.write(f'Bot response: {response}\n')
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST_IP, PORT))

    # Send the initial message
    initial_message = "start ironclad"
    encoded_message = initial_message.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)

    threading.Thread(target=receive_messages, args=(sock, send_message_func)).start()

if __name__ == "__main__":
    main()
