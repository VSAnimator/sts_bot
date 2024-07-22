import os
import json
import string

# Battle file name
battle_file = "/Users/sarukkai/Documents/rl/sts/CommunicationModExtension/src/main/python/runs_raw/1721114507.7982662.txt"

seed = None

# Output file for command log
output_file = "command_log.txt"

# Read the battle file
with open(battle_file, "r") as f:
    battle_data = f.readlines()

def convert_seed_to_string(seed: int) -> str:
    """Converts numeric seed from run file to alphanumeric seed"""
    
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    # Convert to unsigned
    leftover = seed = seed + 2**64 if seed < 0 else seed
    char_count = len(char_string)
    result = []
    while leftover != 0:
        remainder = leftover % char_count
        leftover = leftover // char_count
        index = int(remainder)
        c = char_string[index]
        result.insert(0, c)
    stringSeed = ''.join(result)
    return stringSeed
'''

def convert_seed_to_string(seed_num):
    base_string = "0123456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    result = ""
              
    left_over = seed_num if seed_num >= 0 else (seed_num + (1 << 64))
    base_length = len(base_string)
    
    while left_over != 0:
        remainder = left_over % base_length
        left_over = left_over // base_length
        result = base_string[remainder] + result

    return result
'''

battle_path = None
battle_base_path = "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources/startstates/"

line_count = 0
# Open the output file
with open(output_file, "w") as f:
    # For every line, if "choose " is present, print the line
    for line in battle_data:
        if "seed\":" in line and seed is None:
            seed = convert_seed_to_string(int(line.split("seed\":")[1].split(",")[0]))
            # Also get ascension
            ascension = line.split("ascension_level\":")[1].split(",")[0]
            f.write("start ironclad " + ascension + " " + seed + "\n")
            line_count += 1
            #exit()
        if "Response: " in line and "autoplay" not in line:
            #if "confirm" in line:
                #print("confirm involved ", line)
                #line = line.replace("confirm", "proceed")
                #print(line)
            f.write(line.split("Response: ")[1].strip() + "\n")
            line_count += 1
        elif "battle_log" in line:
            #print(line)
            state = json.loads("{\"" + line)
            floor = state["game_state"]["floor"]
            # Pad floor out to two digits "01", "02", "03", etc.
            floor = str(floor).zfill(2)
            battle_path = battle_base_path + seed + "/" + floor + "/commands.txt"
            # Load the battle file
            with open(battle_path, "r") as battle_file:
                print("File", battle_path, "exists")
                battle_data = battle_file.readlines()
                for elem_big in battle_data:
                    elem_big = json.loads(elem_big)
                    #print(elem_big)
                    commands = elem_big['commands']
                    for elem in commands:
                        #print(elem)
                        if elem == None:
                            continue
                        #if "potion" in elem['command'].lower():
                        #    print("potion involved ", elem)
                        elem = json.loads(elem['command'])
                        #print(elem)
                        if elem == "null":
                            continue
                        command_type = elem["type"]
                        if command_type == "CARD":
                            if "Spot Weakness" in elem['display_string'] and elem['monster_index'] == -1:
                                print('\n')
                                print("Spot Weakness", elem, elem_big)
                                elem["monster_index"] = 0
                            f.write("play " + str(elem["card_index"] + 1) + (" " + str(elem["monster_index"]) if "monster_index" in elem and elem["monster_index"] >= 0 else "") + "\n")
                        elif command_type == "POTION":
                            #print(elem)
                            f.write("potion use " + str(elem["potion_index"]) + " " + (" " + str(elem["monster_index"]) if "monster_index" in elem and elem["monster_index"] >= 0 else "") + "\n")
                        elif command_type == "END":
                            f.write("end\n")
                        elif command_type == "HAND_SELECT" or command_type == "CARD_REWARD_SELECT":
                            f.write("choose " + str(elem["card_index"]) + "\n")
                        else:
                            if "card_index" in elem:
                                f.write("choose " + str(elem["card_index"]) + "\n")
                            else:
                                f.write("proceed \n")
                        line_count += 1

'''
# For every line, if "choose " is present, print the line
for line in battle_data:
    if "seed\":" in line and seed is None:
        seed = line.split("seed\":")[1].split(",")[0]
        print("Seed: ", seed)
        #exit()
    if "Response: " in line and "autoplay" not in line:
        print(line.split("Response: ")[1].strip())
    elif "battle_log" in line:
        #print(line)
        state = json.loads("{\"" + line)
        #print(state["battle_log"])
        for elem in state["battle_log"]:
            print("play " + str(elem["card_index"] + 1) + (" " + str(elem["monster_index"]) if "monster_index" in elem else ""))
#print("Seed: ", seed)
'''