import socket
import threading
from state_parser import parse_game_state
import numpy as np

HOST_IP = "127.0.0.1"
PORT = 8080

def receive_messages(sock, send_message_func):
    while True:
        try:
            msg_length = sock.recv(4)
            if not msg_length:
                break

            msg_length = int.from_bytes(msg_length, byteorder='big')
            message = sock.recv(msg_length).decode('utf-8')
            if message:
                print(message)
                send_message_func(sock, message)
            else:
                break
        except Exception as e:
            print(f"Error: {e}")
            break

def send_message_func(sock, received_message):
    # Try parsing game state
    parsed_state, shared_info = parse_game_state('{"' + received_message)
    print(parsed_state)
    print(shared_info)
    if "autoplay" in parsed_state['available_commands']:
        response = "autoplay"
    else:
        all_options = parsed_state['available_commands']
        # Randomly choose an option
        chosen_option = np.random.choice(all_options)
        # If the chosen option is "choose", randomly choose an index
        if chosen_option == "choose":
            chosen_option = "choose " + str(np.random.randint(0, len(parsed_state['game_state']['choice_list'])))
        response = chosen_option
    #else:
        # Placeholder function: respond based on user input for now
    #    response = input("Response: ") #input(f"Received: {received_message}\nYour response: ")
    print(response)
    encoded_message = response.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)

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
