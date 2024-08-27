import subprocess
import os
import time

# Function to start the subprocess
def start_subprocess(command, working_directory):
    try:
        process = subprocess.Popen(command, cwd=working_directory)
        return process
    except Exception as e:
        print(f"Error starting subprocess: {e}")
        return None

'''
# Function to monitor and kill the subprocess based on a condition
def monitor_and_kill_subprocess(process, condition_check, timeout=300):
    start_time = time.time()
    while True:
        if condition_check():
            print(f"Killing subprocess with PID: {process.pid}")
            os.kill(process.pid, signal.SIGTERM)
            break
        if time.time() - start_time > timeout:
            print("Timeout reached. Terminating subprocess.")
            os.kill(process.pid, signal.SIGTERM)
            break
        time.sleep(1)  # Sleep for a while before checking again

# Example condition check function (replace with actual condition)
def example_condition_check():
    # Example condition: always return False (replace with real condition)
    return False
'''

def start_game():
    # Commands and working directories
    '''
    command1 = [
        "sudo",
        "./jre/bin/java",
        "-Xms1024m",
        "-Xmx2048m",
        "-jar",
        "-DisServer=true",
        "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources/mods/ModTheSpireSigned.jar",
        "--skip-launcher"
    ]
    '''
    command1 = [
        "sudo",
        "./jre/bin/java",
        "-Xms1024m",
        "-Xmx2048m",
        "-jar",
        "-DisServer=true",
        "-DisPlaidMode=true",
        "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources/mods/ModTheSpireSigned.jar",
        "--skip-intro",
        "--skip-launcher"
    ]
    working_directory1 = "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources"

    '''
    command2 = [
        "./jre/bin/java",
        "-jar",
        "/Users/sarukkai/Library/Application Support/Steam/steamapps/workshop/content/646570/1605060445/ModTheSpireSigned2.jar",
        "--skip-intro",
        "--skip-launcher"
    ]
    '''
    command2 = [
        "./jre/bin/java",
        "-Xms1024m",
        "-Xmx2048m",
        "-jar",
        "-DconnectOnStartup=true",
        "-DisPlaidMode=true",
        "/Users/sarukkai/Library/Application Support/Steam/steamapps/workshop/content/646570/1605060445/ModTheSpireSigned2.jar",
        "--skip-intro",
        "--skip-launcher"
    ]
    working_directory2 = "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources"

    # Start the subprocesses
    process1 = start_subprocess(command1, working_directory1)
    process2 = start_subprocess(command2, working_directory2)

    return process1, process2
