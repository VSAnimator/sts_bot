import json
from map_processing import find_shortest_path_to_symbol, traverse_map

# Helper function to find a node by its coordinates
def find_node(x, y, map_data):
    for node in map_data:
        if node['x'] == x and node['y'] == y:
            return node
    return None

# Function to get the linear path until the next branching point
def get_path_until_branch(x, y, map_data):
    path = []
    current_node = find_node(x, y, map_data)
    while current_node and len(current_node['children']) == 1:
        path.append(current_node)
        x, y = current_node['children'][0]['x'], current_node['children'][0]['y']
        current_node = find_node(x, y, map_data)
    if current_node:
        path.append(current_node)
    return path

# Load cards and relics from info folder JSON files
colorless_card_info = json.load(open("info/colorless_cards.json"))
curse_card_info = json.load(open("info/curse_cards.json"))
ironclad_card_info = json.load(open("info/ironclad_cards.json"))
# Combine all card info into one dictionary
ironclad_card_info.update(colorless_card_info)
ironclad_card_info.update(curse_card_info)
# Load relic info
relic_info = json.load(open("info/relics.json"))
# Make all keys in both dicts lowercase
ironclad_card_info = {key.lower(): value for key, value in ironclad_card_info.items()}
relic_info = {key.lower(): value for key, value in relic_info.items()}

def parse_game_state(game_state_json):
    global ironclad_card_info, relic_info
    game_state = json.loads(game_state_json)
    
    if not game_state.get('in_game'):
        return "Not in game"
    
    def generate_card_key(card):
        return f"{card['id']}_upg{card['upgrades']}"
    
    parsed_state = {
        'available_commands': game_state.get('available_commands', []),
        'ready_for_command': game_state.get('ready_for_command', False),
        'game_state': {
            'choice_list': game_state['game_state'].get('choice_list', []),
            'screen_type': game_state['game_state'].get('screen_type', ''),
            'screen_state': game_state['game_state'].get('screen_state', {}),
            'seed': game_state['game_state'].get('seed', 0),
            'deck': [generate_card_key(card) for card in game_state['game_state'].get('deck', [])],
            'relics': [relic['id'] for relic in game_state['game_state'].get('relics', [])],
            'max_hp': game_state['game_state'].get('max_hp', 0),
            'act_boss': game_state['game_state'].get('act_boss', ''),
            'gold': game_state['game_state'].get('gold', 0),
            'action_phase': game_state['game_state'].get('action_phase', ''),
            'act': game_state['game_state'].get('act', 0),
            'screen_name': game_state['game_state'].get('screen_name', ''),
            'room_phase': game_state['game_state'].get('room_phase', ''),
            'is_screen_up': game_state['game_state'].get('is_screen_up', False),
            'potions': [potion['id'] for potion in game_state['game_state'].get('potions', [])],
            'current_hp': game_state['game_state'].get('current_hp', 0),
            'floor': game_state['game_state'].get('floor', 0),
            'ascension_level': game_state['game_state'].get('ascension_level', 0),
            'class': game_state['game_state'].get('class', ''),
        },
    }
    
    # Add battle log if present
    if 'battle_log' in game_state:
        print("Adding battle log")
        parsed_state['battle_log'] = game_state['battle_log']
    else:
        print("No battle log")

    # If "next_nodes" in "screen_state", we will expand them out using "get_path_until_branch"
    if 'next_nodes' in parsed_state['game_state']['screen_state']:
        print("Expanding next nodes")
        next_nodes = parsed_state['game_state']['screen_state']['next_nodes']
        expanded_next_nodes = {}
        for start in next_nodes:
            info_string = ""
            curr_path = get_path_until_branch(start['x'], start['y'], game_state['game_state']['map'])
            branching_length = len(curr_path)
            info_string += "Steps to next branch: " + str(branching_length)
            map_nodes = game_state['game_state']['map']
            _, _, max_m, min_m = traverse_map(map_nodes, start['x'], start['y'], "M", 10)
            info_string += ". In the next 10 nodes: min_monsters=" + str(min_m) + ", max_monsters=" + str(max_m)
            _, _, max_e, min_e = traverse_map(map_nodes, start['x'], start['y'], "E", 10)
            info_string += ", min_elites=" + str(min_e) + ", max_elites=" + str(max_e)
            shop_path = find_shortest_path_to_symbol(map_nodes, start['x'], start['y'], "$")
            info_string += ". Dist to shop: " + str(len(shop_path))
            rest_path = find_shortest_path_to_symbol(map_nodes, start['x'], start['y'], "R")
            info_string += ". Dist to rest: " + str(len(rest_path))
            expanded_next_nodes["x=" + str(start['x'])] = info_string
        #print("Expanded next nodes", expanded_next_nodes)
        parsed_state['game_state']['screen_state']['next_node_info'] = expanded_next_nodes

    # For the choice list, if the elemnts are "card" or "relic", add the card or relic info to "choice_info" field in parsed_state
    choice_info = {}
    for i, choice in enumerate(parsed_state['game_state']['choice_list']):
        print("Choice", choice)
        if choice in ironclad_card_info:
            choice_info[choice] = ironclad_card_info[choice]['effect']
        elif choice in relic_info:
            choice_info[choice] = relic_info[choice]['effect']
    parsed_state['game_state']['choice_info'] = choice_info

    # Shared information dictionaries
    card_info = {generate_card_key(card): card for card in game_state['game_state'].get('deck', [])}
    relic_info = {relic['id']: relic for relic in game_state['game_state'].get('relics', [])}
    potion_info = {potion['id']: potion for potion in game_state['game_state'].get('potions', [])}

    # Remove 'key', 'click', 'wait', 'state' from available commands
    parsed_state['available_commands'] = [command for command in parsed_state['available_commands'] if command not in ['key', 'click', 'wait', 'state', 'return', 'cancel', 'potion', 'recall']]
    
    shared_info = {
        'cards': card_info,
        'relics': relic_info,
        'potions': potion_info
    }
    
    return parsed_state, shared_info
