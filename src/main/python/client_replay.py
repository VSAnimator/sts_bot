import socket
import threading
import time
from state_parser import parse_game_state
from battle_log_parser import extract_battle_info
import numpy as np
import ast
from launch_game import start_game
import os
import signal
import select

HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 15000 #* 100 # 5 minutes

exception_count = 0

def receive_messages(sock, send_message_func):
    global exception_count
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
                    override = False
                    if current_time - last_activity_time > TIMEOUT_THRESHOLD:
                        print("Emergency override")
                        override = True
                    
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
                    if override:
                        send_message_func(sock, "message", log_file, raw_log_file)
                    exception_count = 0

                except Exception as e:
                    print(e)
                    exit()
                    print(f"Exception in receive_messages: {e}")
                    # Send a message with the content "state" to the server
                    # Then continue
                    exception_count += 1
                    state_message = "state"
                    if exception_count == 5:
                        # Maybe we just need to start a new game
                        state_message = "start ironclad 10"
                        new_run = True
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
last_message = "start ironclad 10"

# Open file with commands
with open("command_logs/1722058666.txt", "r") as f:
    commands = f.read().split("\n")

def send_message_func(sock, received_message, log_file, raw_log_file):
    global message_count, autoplay_count, last_message, last_time, total_autoplay_time, start_time, commands
    if last_message == "autoplay":
        total_autoplay_time += time.time() - last_time
    last_time = time.time()
    # Try parsing game state
    #parsed_state, shared_info = parse_game_state('{"' + received_message)
    #all_options = parsed_state['available_commands']
    # Get the next action from the file
    chosen_option = commands[message_count]
    response = chosen_option
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