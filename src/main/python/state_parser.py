import json

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
            'class': game_state['game_state'].get('class', '')
        }
    }
    
    # Shared information dictionaries
    card_info = {generate_card_key(card): card for card in game_state['game_state'].get('deck', [])}
    relic_info = {relic['id']: relic for relic in game_state['game_state'].get('relics', [])}
    potion_info = {potion['id']: potion for potion in game_state['game_state'].get('potions', [])}

    # Remove 'key', 'click', 'wait', 'state' from available commands
    parsed_state['available_commands'] = [command for command in parsed_state['available_commands'] if command not in ['key', 'click', 'wait', 'state', 'return', 'cancel', 'potion']]
    
    shared_info = {
        'cards': card_info,
        'relics': relic_info,
        'potions': potion_info
    }
    
    return parsed_state, shared_info

# Example JSON string (full string as provided)
game_state_json = '''
{
    "available_commands":["choose","potion","proceed","key","click","wait","state"],
    "ready_for_command":true,
    "in_game":true,
    "game_state":{
        "choice_list":["gold"],
        "screen_type":"COMBAT_REWARD",
        "screen_state":{
            "rewards":[{"gold":61,"reward_type":"GOLD"}]
        },
        "seed":-1536158724164635181,
        "deck":[
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Strike","id":"Strike_R","type":"ATTACK","ethereal":false,"uuid":"ba8694d9-b676-4766-9d64-a5ae7d158f8c","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Strike","id":"Strike_R","type":"ATTACK","ethereal":false,"uuid":"f63f0922-25a3-45a3-9a77-a5044ce74425","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Strike","id":"Strike_R","type":"ATTACK","ethereal":false,"uuid":"62f58317-c1cb-4ad8-ad0e-e0183ea0428c","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Strike","id":"Strike_R","type":"ATTACK","ethereal":false,"uuid":"749c7577-580e-40e5-b418-45fa6a8c52e1","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Strike","id":"Strike_R","type":"ATTACK","ethereal":false,"uuid":"c68fced8-fc25-4512-bd4f-f04779c89b9d","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Defend","id":"Defend_R","type":"SKILL","ethereal":false,"uuid":"e41487f3-7641-4d7e-b07e-3e5b0a62b073","upgrades":0,"rarity":"BASIC","has_target":false},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Defend","id":"Defend_R","type":"SKILL","ethereal":false,"uuid":"60c86cf4-cd21-4fa9-8991-2357a569e8b1","upgrades":0,"rarity":"BASIC","has_target":false},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Defend","id":"Defend_R","type":"SKILL","ethereal":false,"uuid":"4d483dc4-2bde-4c35-8cc7-371f1dd321d7","upgrades":0,"rarity":"BASIC","has_target":false},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Defend","id":"Defend_R","type":"SKILL","ethereal":false,"uuid":"3e18793e-cdf0-48c3-96ff-9477961c0571","upgrades":0,"rarity":"BASIC","has_target":false},
            {"exhausts":false,"is_playable":false,"cost":2,"name":"Bash","id":"Bash","type":"ATTACK","ethereal":false,"uuid":"5122e1af-8f2a-45bc-9975-258285d1045d","upgrades":0,"rarity":"BASIC","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":2,"name":"Perfected Strike","id":"Perfected Strike","type":"ATTACK","ethereal":false,"uuid":"4e83734d-3e76-4790-bf95-022f9487545d","upgrades":0,"rarity":"COMMON","has_target":true},
            {"exhausts":false,"is_playable":false,"cost":1,"name":"Cleave","id":"Cleave","type":"ATTACK","ethereal":false,"uuid":"594e0106-7595-45ed-92a7-6f25fbad18df","upgrades":0,"rarity":"COMMON","has_target":false},
            {"exhausts":false,"is_playable":false,"cost":2,"name":"Perfected Strike","id":"Perfected Strike","type":"ATTACK","ethereal":false,"uuid":"51f9b873-281b-487f-b3ac-e7b9005b8812","upgrades":0,"rarity":"COMMON","has_target":true},
            {"exhausts":true,"is_playable":false,"cost":2,"name":"Reaper","id":"Reaper","type":"ATTACK","ethereal":false,"uuid":"a6d48240-e4d8-4e16-a0df-7b8f7b932734","upgrades":0,"rarity":"RARE","has_target":false}
        ],
        "relics":[
            {"name":"Burning Blood","id":"Burning Blood","counter":-1},
            {"name":"Neow's Lament","id":"NeowsBlessing","counter":-2},
            {"name":"Mercury Hourglass","id":"Mercury Hourglass","counter":-1}
        ],
        "max_hp":85,
        "act_boss":"Hexaghost",
        "gold":210,
        "action_phase":"WAITING_ON_USER",
        "act":1,
        "screen_name":"COMBAT_REWARD",
        "room_phase":"COMPLETE",
        "is_screen_up":true,
        "potions":[
            {"requires_target":true,"can_use":false,"can_discard":true,"name":"Weak Potion","id":"Weak Potion"},
            {"requires_target":false,"can_use":false,"can_discard":false,"name":"Potion Slot","id":"Potion Slot"},
            {"requires_target":false,"can_use":false,"can_discard":false,"name":"Potion Slot","id":"Potion Slot"}
        ],
        "current_hp":56,
        "floor":7,
        "ascension_level":0,
        "class":"IRONCLAD"
    }
}
'''

parsed_state, shared_info = parse_game_state(game_state_json)
print("Parsed state", parsed_state)
print("Shared info", shared_info)
