import json

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

def parse_game_state(game_state_json):
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
            curr_path = get_path_until_branch(start['x'], start['y'], game_state['game_state']['map'])
            expanded_next_nodes["x=" + str(start['x'])] = str.join("",[node['symbol'] for node in curr_path])
        print("Expanded next nodes", expanded_next_nodes)
        parsed_state['game_state']['screen_state']['expanded_next_nodes'] = expanded_next_nodes

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
