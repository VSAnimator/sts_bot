import socket
import time
import select
import sys

HOST_IP = "127.0.0.1"
PORT = 8080
TIMEOUT_THRESHOLD = 1000

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST_IP, PORT))
        print("Connected to the server.")
    except Exception as e:
        print(f"Exception in connecting to the server: {e}")
        return

    # Send the initial message
    initial_message = "load startstates/4ZNJ22MUNT7DX/06/saves/IRONCLAD.autosave"
    encoded_message = initial_message.encode('utf-8')
    sock.sendall(len(encoded_message).to_bytes(4, byteorder='big'))
    sock.sendall(encoded_message)
    print("Initial message sent.")

    last_state_time = time.time()
    last_activity_time = time.time()

    while True:
        try:
            # Send "state" message every second
            if time.time() - last_state_time >= 100:
                state_message = "state"
                encoded_state_message = state_message.encode('utf-8')
                sock.sendall(len(encoded_state_message).to_bytes(4, byteorder='big'))
                sock.sendall(encoded_state_message)
                print("Sent state message.")
                last_state_time = time.time()

            # Use select to handle non-blocking input and socket operations
            read_sockets, _, _ = select.select([sock, sys.stdin], [], [], 1.0)

            if not read_sockets:
                if time.time() - last_activity_time > TIMEOUT_THRESHOLD:
                    print("No activity for 10 seconds. Exiting.")
                    break

            for s in read_sockets:
                if s == sock:
                    # Receive message from server
                    msg_length = sock.recv(4)
                    if msg_length:
                        msg_length = int.from_bytes(msg_length, byteorder='big')
                        message = sock.recv(msg_length)
                        if message:
                            try:
                                decoded_message = message.decode('utf-8')
                                print(f"Received: {decoded_message}")
                            except UnicodeDecodeError:
                                print(f"Received (binary data): {message}")
                        else:
                            print("Empty message received. Continuing.")
                        last_activity_time = time.time()
                    else:
                        print("No message length received. Continuing.")
                        last_activity_time = time.time()

                elif s == sys.stdin:
                    # Check for user input
                    user_input = sys.stdin.readline().strip()
                    if user_input:
                        encoded_user_message = user_input.encode('utf-8')
                        sock.sendall(len(encoded_user_message).to_bytes(4, byteorder='big'))
                        sock.sendall(encoded_user_message)
                        last_activity_time = time.time()

        except Exception as e:
            print(f"Exception in main loop: {e}")
            break

    sock.close()
    print("Connection closed.")

if __name__ == "__main__":
    main()
