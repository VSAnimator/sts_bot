import asyncio
import json
import os
import socket
import subprocess
import time
from twitchio.ext import commands

HOST_IP = "127.0.0.1"
CLIENT_PROFILE = "Client"
SERVER_PROFILE = "Server"
CLIENT_MODDED_PROFILE = "Client_modded"
SERVER_MODDED_PROFILE = "Server_modded"

CLIENT_GAME_PORT = 5123
SERVER_GAME_PORT = 5124

FIVE_MINUTES = 1000 * 60 * 5

game_input_stream = None
game_output_stream = None

server_input_stream = None
server_output_stream = None

client_game_process = None
server_game_process = None

client_game_socket = None
server_game_socket = None

client_game_server_socket = None
server_game_server_socket = None

should_kill_client_game = False
should_kill_server_game = False

should_send_enable = True

is_client_active = False
is_server_active = False

started_start_thread = False

twitch_config = None

class Bot(commands.Bot):

    def __init__(self, token, prefix):
        super().__init__(token=token, prefix=prefix)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def event_message(self, message):
        if message.author.is_mod or message.author.is_broadcaster:
            content_tokens = message.content.split(" ")

            if len(content_tokens) >= 2:
                if content_tokens[0] == "!admin":
                    command = content_tokens[1]
                    if command == "startgame":
                        await self.send_message("Starting Game")
                        if client_game_process is None or client_game_process.poll() is not None:
                            start_running_game()
                    elif command == "restartserver":
                        await self.send_message("Request Server Restart")
                        global should_kill_server_game
                        should_kill_server_game = True
                    elif command == "winbattle":
                        await self.send_message("Sending Kill All")
                        send_kill()
                    elif command == "restartall":
                        await self.send_message("Requesting Restart All")
                        global should_kill_client_game
                        should_kill_client_game = True
                        should_kill_server_game = True
                        start_game_after_start()
                    elif command == "state":
                        await self.send_message("Requesting State Update")
                        request_state()
                    elif command == "advancegame":
                        await self.send_message("Requesting Game Advance")
                        request_advance_battle()
                    elif command == "losebattle":
                        await self.send_message("Requesting Battle Loss")
                        request_battle_loss()
                    elif command == "enablemods":
                        await self.send_message("enabling mods (on restart)")
                        global is_modded
                        is_modded = True
                    elif command == "disablemods":
                        await self.send_message("disabling mods (on restart)")
                        is_modded = False
                    elif command == "loserelic":
                        if len(content_tokens) >= 3:
                            await self.send_message("Requesting relic loss")
                            request_lose_relic(content_tokens[2])
                    elif command == "addkeys":
                        await self.send_message("Requesting All Keys")
                        request_all_keys()
                    elif command == "addrelic":
                        if len(content_tokens) >= 3:
                            await self.send_message("Requesting relic add")
                            request_add_relic(content_tokens[2])
                    elif command == "loadlegacy":
                        if len(content_tokens) >= 4:
                            await self.send_message("Attempting Load Request")
                            try:
                                send_load_request("C:/stuff/rundata/runs", content_tokens[2], int(content_tokens[3]))
                            except Exception as e:
                                print(e)
                    elif command == "load":
                        if len(content_tokens) >= 3:
                            await self.send_message("Attempting Load Request")
                            try:
                                send_load_request("C:/stuff/_ModTheSpire/startstates", content_tokens[2], int(content_tokens[3]))
                            except Exception as e:
                                print(e)

    async def send_message(self, message):
        await self.get_channel(twitch_config['channel']).send(f"[Admin BOT] {message}")

def read_twitch_config():
    with open('twitch_config.json', 'r') as file:
        return json.load(file)

def start_client_game():
    try:
        client_profile_name = CLIENT_MODDED_PROFILE if is_modded else CLIENT_PROFILE
        command = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'java', 'bin', 'java'), 
            '-jar', 
            '-DisClient=true', 
            'C:\\stuff\\_ModTheSpire\\ModTheSpire.jar', 
            '--profile', client_profile_name, 
            '--skip-launcher', 
            '--skip-intro'
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(f"logs/client/stdout-{int(time.time())}.txt", "w") as stdout, open(f"logs/client/stderr-{int(time.time())}.txt", "w") as stderr:
            asyncio.create_task(read_stream(process.stdout, stdout))
            asyncio.create_task(read_stream(process.stderr, stderr))

        send_message("Client Launched, Waiting for Startup Signal...")
        wait_for_client_success_signal()
        return process
    except Exception as e:
        print(e)
    return None

def start_server_game():
    try:
        server_profile_name = SERVER_MODDED_PROFILE if is_modded else SERVER_PROFILE
        command = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'java', 'bin', 'java'), 
            '-Xms1024m', 
            '-Xmx2048m', 
            '-jar', 
            '-DisServer=true', 
            'C:\\stuff\\_ModTheSpire\\ModTheSpire.jar', 
            '--profile', server_profile_name, 
            '--skip-launcher', 
            '--skip-intro'
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(f"logs/server/stdout-{int(time.time())}.txt", "w") as stdout, open(f"logs/server/stderr-{int(time.time())}.txt", "w") as stderr:
            asyncio.create_task(read_stream(process.stdout, stdout))
            asyncio.create_task(read_stream(process.stderr, stderr))

        send_message("Server Launched, Waiting for Startup Signal...")
        wait_for_server_success_signal()
        return process
    except Exception as e:
        print(e)
    return None

async def read_stream(stream, file):
    while True:
        line = await stream.readline()
        if not line:
            break
        print(line.decode('utf-8').strip())
        file.write(line.decode('utf-8'))
        file.flush()

def wait_for_client_success_signal():
    async def inner():
        global client_game_socket, game_input_stream, game_output_stream, is_client_active
        try:
            if client_game_socket:
                client_game_socket.close()
            client_game_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_game_server_socket.bind((HOST_IP, CLIENT_GAME_PORT))
            client_game_server_socket.listen(1)
            client_game_socket, _ = client_game_server_socket.accept()
            game_input_stream = client_game_socket.makefile('rb')
            game_output_stream = client_game_socket.makefile('wb')
            await asyncio.sleep(2)
            send_message("Client Startup Message Received")
            is_client_active = True
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def wait_for_server_success_signal():
    async def inner():
        global server_game_socket, server_input_stream, server_output_stream, is_server_active
        try:
            if server_game_socket:
                server_game_socket.close()
            server_game_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_game_server_socket.bind((HOST_IP, SERVER_GAME_PORT))
            server_game_server_socket.listen(1)
            server_game_socket, _ = server_game_server_socket.accept()
            server_input_stream = server_game_socket.makefile('rb')
            server_output_stream = server_game_socket.makefile('wb')
            await asyncio.sleep(2)
            send_message("Server Startup Message Received")
            is_server_active = True
            if is_client_active:
                request_battle_restart()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_state():
    async def inner():
        try:
            game_output_stream.write(b'state\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def send_enable():
    async def inner():
        try:
            game_output_stream.write(b'enable\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def send_kill():
    async def inner():
        try:
            game_output_stream.write(b'kill\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_battle_restart():
    async def inner():
        try:
            game_output_stream.write(b'battlerestart\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_advance_battle():
    async def inner():
        try:
            game_output_stream.write(b'advancegame\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_all_keys():
    async def inner():
        try:
            game_output_stream.write(b'addkeys\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_battle_loss():
    async def inner():
        try:
            game_output_stream.write(b'losebattle\n')
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_lose_relic(relic_name):
    async def inner():
        try:
            game_output_stream.write(f'loserelic {relic_name}\n'.encode('utf-8'))
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def request_add_relic(relic_name):
    async def inner():
        try:
            game_output_stream.write(f'addrelic {relic_name}\n'.encode('utf-8'))
            game_output_stream.flush()
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def send_load_request(root, seed, floor_num):
    async def inner():
        try:
            floor_dir = f"{root}/{seed}/{floor_num:02d}"
            paths = [p for p in os.listdir(floor_dir) if p.endswith("autosave")]
            if paths:
                path = os.path.join(floor_dir, paths[0])
                player_class = paths[0].split(".")[0]
                send_load_request_inner(path, player_class, 1, 0)
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def send_load_request_inner(path, player_class, start, end):
    async def inner():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST_IP, 5200))
                request_json = {
                    "command": "load",
                    "replay_floor_start": start,
                    "replay_floor_end": end,
                    "path": path,
                    "playerClass": player_class
                }
                s.sendall(json.dumps(request_json).encode('utf-8'))
                s.settimeout(5)
                response = s.recv(4096).decode('utf-8')
                print(response)
        except Exception as e:
            print(e)
    asyncio.create_task(inner())

def track_client_process():
    async def inner():
        global client_game_process
        while True:
            if client_game_process and client_game_process.poll() is None:
                if should_kill_client_game:
                    global is_client_active, should_kill_client_game
                    is_client_active = False
                    should_kill_client_game = False
                    client_game_process.terminate()
                await asyncio.sleep(3)
            else:
                client_game_process = start_client_game()
                track_client_process()
                start_game_after_start()
                return
    asyncio.create_task(inner())

def track_server_process():
    async def inner():
        global server_game_process
        while True:
            if server_game_process and server_game_process.poll() is None:
                if should_kill_server_game:
                    global is_server_active, should_kill_server_game
                    is_server_active = False
                    should_kill_server_game = False
                    server_game_process.terminate()
            else:
                if not is_client_active:
                    await asyncio.sleep(3)
                server_game_process = start_server_game()
                track_server_process()
                return
            await asyncio.sleep(3)
    asyncio.create_task(inner())

def start_game_after_start():
    async def inner():
        global started_start_thread
        while not started_start_thread:
            if is_client_active and is_server_active and not should_kill_server_game and not should_kill_client_game:
                started_start_thread = True
                await bot.send_message("Running Game Found Sending Enable in 10 seconds...")
                await asyncio.sleep(10)
                send_enable()
                await bot.send_message("Enable Sent, Requesting State update in 2 seconds...")
                await asyncio.sleep(2)
                request_state()
                await bot.send_message("Game Started")
                return
            await asyncio.sleep(0.5)
    asyncio.create_task(inner())

def start_running_game():
    global client_game_process, server_game_process
    client_game_process = start_client_game()
    server_game_process = start_server_game()
    asyncio.create_task(track_client_process())
    asyncio.create_task(track_server_process())
    start_game_after_start()

def send_message(message):
    asyncio.create_task(bot.send_message(message))

if __name__ == "__main__":
    twitch_config = read_twitch_config()
    bot = Bot(twitch_config['token'], '!')
    bot.run()
