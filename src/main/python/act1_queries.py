import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np
from collections import Counter

db = dataset.connect('sqlite:///act1.db')

# Create tables for runs and for individual states
run_table = db['runs']
state_table = db['states']

# States columns
state_cols = ['id', 'game_state_choice_list', 'game_state_screen_type', 'game_state_seed', 'game_state_deck', 'game_state_relics', 'game_state_max_hp', 'game_state_act_boss', 'game_state_gold', 'game_state_action_phase', 'game_state_act', 'game_state_screen_name', 'game_state_room_phase', 'game_state_is_screen_up', 'game_state_potions', 'game_state_current_hp', 'game_state_floor', 'game_state_ascension_level', 'game_state_class', 'game_state_choice_info', 'available_commands', 'ready_for_command', 'bot_response', 'run_id', 'step', 'timestamp', 'event_name', 'battle_log']

def calculate_similarity(state, current_state):
    # Calculate similarity score based on attributes
    similarity = 0
    similarity += 100 - abs(state['game_state_current_hp'] - current_state['current_hp'])
    similarity += 100 - abs(state['game_state_max_hp'] - current_state['max_hp'])
    similarity += 100 - abs(state['game_state_floor'] - current_state['floor'])
    similarity += 100 - abs(state['game_state_ascension_level'] - current_state['ascension_level'])

    # Calculate similarity for deck
    current_deck = Counter(ast.literal_eval(state['game_state_deck']))
    # In target deck, replace _upg0 with "" and _upg1 with "+" to match current deck format
    target_deck = Counter(current_state['deck'])
    deck_similarity = sum((current_deck & target_deck).values()) / max(sum(target_deck.values()), sum(current_deck.values()))
    #print("deck similarity", deck_similarity)
    similarity += deck_similarity * 100
    #print("Deck similarity:", deck_similarity)

    # Calculate similarity for relics
    current_relics = set(ast.literal_eval(state['game_state_relics']))
    target_relics = set(current_state['relics'])
    relics_similarity = len(current_relics & target_relics) / len(target_relics)
    similarity += relics_similarity * 100
    #print("Relics similarity:", relics_similarity)

    return similarity

# Goal: return similar states to this one, ranked
# Additional_filters can include HP conditions, etc if desired
def similarity_query(current_state, additional_filters, victory):
    try:
        query = f"""
        select states.*
        from runs, states
        where runs.id == states.run_id
        and runs.victory == {victory}
        and game_state_screen_type == "{current_state['game_state']['screen_type']}"
        AND ({additional_filters})
        AND game_state_floor BETWEEN {current_state['game_state']['floor'] - 3} AND {current_state['game_state']['floor'] + 3}
        AND game_state_ascension_level = {current_state['game_state']['ascension_level']}
        """

        result = db.query(query)

        final_result = []
        for state in result:
            state['similarity'] = calculate_similarity(state, current_state['game_state'])
            final_result.append(state)
        
        # Sort by similarity, return top 5
        final_result.sort(reverse=True, key=lambda x: x['similarity'])

        return final_result
    except:
        return None

def event_query(current_state, victory):
    print("Event name:", current_state['game_state']['screen_state']['event_name'])
    return similarity_query(current_state, f'''event_name == "{current_state['game_state']['screen_state']['event_name']}"''', victory)

def card_choice_query(current_state, victory):
    current_choice_list = current_state['game_state']['choice_list']
    choices_condition = " OR ".join(
        [f"game_state_choice_info LIKE '%{choice}%'" for choice in current_choice_list if choice != 'skip']
    )

    return similarity_query(current_state, choices_condition, victory)

def campfire_query(current_state, victory):
    choices_condition = f"""abs((game_state_current_hp * 1.0 / game_state_max_hp) - ({current_state['game_state']['current_hp']} * 1.0 / {current_state['game_state']['max_hp']})) < 0.3"""

    return similarity_query(current_state, choices_condition, victory)

def smithing_query(current_state, victory):
    return similarity_query(current_state, "1 == 1", victory)

def map_query(current_state, victory):
    return similarity_query(current_state, "next_node_info is not Null", victory)

test_states = {
    'smithing': {'available_commands': ['choose'], 'ready_for_command': True, 'game_state': {'choice_list': ['strike', 'strike', 'strike', 'strike', 'strike', 'defend', 'defend', 'defend', 'bash', 'twin strike', 'disarm', 'fire breathing', 'carnage'], 'screen_type': 'GRID', 'screen_state': {'cards': [{'exhausts': False, 'cost': 1, 'name': 'Strike', 'id': 'Strike_R', 'type': 'ATTACK', 'ethereal': False, 'uuid': '5d9f2aa6-f71f-4dc7-80a0-90254c1e06e7', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Strike', 'id': 'Strike_R', 'type': 'ATTACK', 'ethereal': False, 'uuid': '8dc1d1ea-6c6a-45e8-bfa3-28dd58b70630', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Strike', 'id': 'Strike_R', 'type': 'ATTACK', 'ethereal': False, 'uuid': '40b4dc62-8598-4157-8156-57c935ec853d', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Strike', 'id': 'Strike_R', 'type': 'ATTACK', 'ethereal': False, 'uuid': 'e9598ccc-e1e5-4983-b8a5-d27f3099a357', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Strike', 'id': 'Strike_R', 'type': 'ATTACK', 'ethereal': False, 'uuid': 'e703f460-e97d-42a0-89e3-eefd9c1d741e', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Defend', 'id': 'Defend_R', 'type': 'SKILL', 'ethereal': False, 'uuid': '4c91f474-f253-4046-a9dd-fc9942d3c88d', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': False}, {'exhausts': False, 'cost': 1, 'name': 'Defend', 'id': 'Defend_R', 'type': 'SKILL', 'ethereal': False, 'uuid': '9562a8ac-3432-4eab-8b45-8a819eca40aa', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': False}, {'exhausts': False, 'cost': 1, 'name': 'Defend', 'id': 'Defend_R', 'type': 'SKILL', 'ethereal': False, 'uuid': 'e727ee2d-c42b-4cee-ab03-263505ed36d8', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': False}, {'exhausts': False, 'cost': 2, 'name': 'Bash', 'id': 'Bash', 'type': 'ATTACK', 'ethereal': False, 'uuid': 'bfe98bd0-523d-4537-8bfe-eb9a3dcb9bfa', 'upgrades': 0, 'rarity': 'BASIC', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Twin Strike', 'id': 'Twin Strike', 'type': 'ATTACK', 'ethereal': False, 'uuid': 'f765a502-dd22-47cb-8eb0-b983f905a8f0', 'upgrades': 0, 'rarity': 'COMMON', 'has_target': True}, {'exhausts': True, 'cost': 1, 'name': 'Disarm', 'id': 'Disarm', 'type': 'SKILL', 'ethereal': False, 'uuid': '0fc83de1-2bc8-4ec9-b3f2-30e0c2551372', 'upgrades': 0, 'rarity': 'UNCOMMON', 'has_target': True}, {'exhausts': False, 'cost': 1, 'name': 'Fire Breathing', 'id': 'Fire Breathing', 'type': 'POWER', 'ethereal': False, 'uuid': '7e4aae2d-381a-4804-b5e6-0e9c3b0247a1', 'upgrades': 0, 'rarity': 'UNCOMMON', 'has_target': False}, {'exhausts': False, 'cost': 2, 'name': 'Carnage', 'id': 'Carnage', 'type': 'ATTACK', 'ethereal': True, 'uuid': 'adc1df36-ac69-42b1-9cbe-0084dbe8e967', 'upgrades': 0, 'rarity': 'UNCOMMON', 'has_target': True}], 'selected_cards': [], 'for_transform': False, 'confirm_up': False, 'any_number': False, 'for_upgrade': True, 'num_cards': 1, 'for_purge': False}, 'seed': 135782151282524851, 'deck': ['AscendersBane_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0', 'Twin Strike_upg0', 'Disarm_upg0', 'Fire Breathing_upg0', 'Carnage_upg0'], 'relics': ['Burning Blood', 'Torii', 'Mango'], 'max_hp': 94, 'act_boss': 'The Guardian', 'gold': 44, 'action_phase': 'WAITING_ON_USER', 'act': 1, 'screen_name': 'GRID', 'room_phase': 'INCOMPLETE', 'is_screen_up': True, 'potions': ['Potion Slot', 'Potion Slot', 'Potion Slot'], 'current_hp': 94, 'floor': 6, 'ascension_level': 10, 'class': 'IRONCLAD', 'choice_info': {'strike': 'Deal 6 (9) damage.', 'defend': 'Gain 5 (8) Block.', 'bash': 'Deal 8 (10) damage. Apply 2 (3) Vulnerable.', 'twin strike': 'Deal 5 (7) damage twice.', 'disarm': 'Enemy loses 2 (3) Strength. Exhaust.', 'fire breathing': 'Whenever you draw a Status or Curse card, deal 6 (10) damage to ALL enemies.', 'carnage': 'Ethereal. Deal 20 (28) damage.'}}},
    'map': {'available_commands': ['choose'], 'ready_for_command': True, 'game_state': {'choice_list': ['x=2', 'x=3', 'x=6'], 'screen_type': 'MAP', 'screen_state': {'first_node_chosen': False, 'current_node': {'x': 0, 'y': -1}, 'boss_available': False, 'next_nodes': [{'symbol': 'M', 'x': 2, 'y': 0}, {'symbol': 'M', 'x': 3, 'y': 0}, {'symbol': 'M', 'x': 6, 'y': 0}], 'next_node_info': {'x=2': 'Steps to next branch: 5. In the next 10 nodes: min_monsters=4, max_monsters=6, min_elites=1, max_elites=3. Dist to shop: 14. Dist to rest: 6', 'x=3': 'Steps to next branch: 2. In the next 10 nodes: min_monsters=2, max_monsters=6, min_elites=1, max_elites=3. Dist to shop: 14. Dist to rest: 6', 'x=6': 'Steps to next branch: 2. In the next 10 nodes: min_monsters=2, max_monsters=7, min_elites=1, max_elites=3. Dist to shop: 3. Dist to rest: 6'}}, 'seed': -8407456421700584771, 'deck': ['AscendersBane_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg1'], 'relics': ['Burning Blood'], 'max_hp': 80, 'act_boss': 'The Guardian', 'gold': 99, 'action_phase': 'WAITING_ON_USER', 'act': 1, 'screen_name': 'MAP', 'room_phase': 'COMPLETE', 'is_screen_up': True, 'potions': ['Potion Slot', 'Potion Slot', 'Potion Slot'], 'current_hp': 72, 'floor': 0, 'ascension_level': 10, 'class': 'IRONCLAD', 'choice_info': {}}},
    'campfire': {'available_commands': ['choose'], 'ready_for_command': True, 'game_state': {'choice_list': ['rest', 'smith', 'recall'], 'screen_type': 'REST', 'screen_state': {'has_rested': False, 'rest_options': ['rest', 'smith', 'recall']}, 'seed': -7945293866597146631, 'deck': ['AscendersBane_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0', 'Anger_upg0', 'Battle Trance_upg1', 'Rampage_upg1', 'Infernal Blade_upg0', 'Feel No Pain_upg0', 'True Grit_upg0', 'Burning Pact_upg0', 'Infernal Blade_upg0'], 'relics': ['Burning Blood', 'Eternal Feather', 'Bottled Flame'], 'max_hp': 96, 'act_boss': 'Hexaghost', 'gold': 97, 'action_phase': 'WAITING_ON_USER', 'act': 1, 'screen_name': 'NONE', 'room_phase': 'INCOMPLETE', 'is_screen_up': False, 'potions': ['Potion Slot', 'Swift Potion', 'Potion Slot'], 'current_hp': 50, 'floor': 15, 'ascension_level': 10, 'class': 'IRONCLAD', 'choice_info': {}}},
    'card_choice': {'available_commands': ['choose', 'skip'], 'ready_for_command': True, 'game_state': {'choice_list': ['iron wave', 'clash', 'ghostly armor'], 'screen_type': 'CARD_REWARD', 'screen_state': {'cards': [{'exhausts': False, 'is_playable': False, 'cost': 1, 'name': 'Iron Wave', 'id': 'Iron Wave', 'type': 'ATTACK', 'ethereal': False, 'uuid': '35619332-953f-43ba-82c6-c028b8d3c98c', 'upgrades': 0, 'rarity': 'COMMON', 'has_target': True}, {'exhausts': False, 'is_playable': False, 'cost': 0, 'name': 'Clash', 'id': 'Clash', 'type': 'ATTACK', 'ethereal': False, 'uuid': 'e41af30e-d836-418c-b52c-08fde0a37bcb', 'upgrades': 0, 'rarity': 'COMMON', 'has_target': True}, {'exhausts': False, 'is_playable': False, 'cost': 1, 'name': 'Ghostly Armor', 'id': 'Ghostly Armor', 'type': 'SKILL', 'ethereal': True, 'uuid': 'bc98e569-aa7c-4b8d-a49a-147608525721', 'upgrades': 0, 'rarity': 'UNCOMMON', 'has_target': False}], 'bowl_available': False, 'skip_available': True}, 'seed': -8400455833619182461, 'deck': ['AscendersBane_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0'], 'relics': ['Burning Blood', 'Unceasing Top'], 'max_hp': 80, 'act_boss': 'Hexaghost', 'gold': 109, 'action_phase': 'WAITING_ON_USER', 'act': 1, 'screen_name': 'CARD_REWARD', 'room_phase': 'COMPLETE', 'is_screen_up': True, 'potions': ['Potion Slot', 'Potion Slot', 'Potion Slot'], 'current_hp': 50, 'floor': 1, 'ascension_level': 10, 'class': 'IRONCLAD', 'choice_info': {'iron wave': 'Gain 5 (7) Block. Deal 5 (7) damage.', 'clash': 'Can only be played if every card in your hand is an Attack. Deal 14 (18) damage.', 'ghostly armor': 'Ethereal. Gain 10 (13) Block.'}}},
    'event': {'available_commands': ['choose'], 'ready_for_command': True, 'game_state': {'choice_list': ['pray', 'leave'], 'screen_type': 'EVENT', 'screen_state': {'event_id': 'Purifier', 'body_text': 'Before you lies an elaborate shrine to a forgotten spirit.', 'options': [{'choice_index': 0, 'disabled': False, 'text': '[Pray] Remove a card from your deck.', 'label': 'Pray'}, {'choice_index': 1, 'disabled': False, 'text': '[Leave]', 'label': 'Leave'}], 'event_name': 'Purifier'}, 'seed': 7366946429734955887, 'deck': ['AscendersBane_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0', 'Clothesline_upg0', 'Armaments_upg0', 'True Grit_upg0', 'Burning Pact_upg0'], 'relics': ['Burning Blood'], 'max_hp': 80, 'act_boss': 'The Guardian', 'gold': 114, 'action_phase': 'WAITING_ON_USER', 'act': 1, 'screen_name': 'NONE', 'room_phase': 'EVENT', 'is_screen_up': False, 'potions': ['Regen Potion', 'Potion Slot', 'Potion Slot'], 'current_hp': 75, 'floor': 5, 'ascension_level': 10, 'class': 'IRONCLAD', 'choice_info': {}}},
}

def test_query(query_name):
    # Call correct subfunction with correct state
    return globals()[query_name + "_query"](test_states[query_name], 0)

'''
for test in test_states:
    print("Test type", test)
    x = test_query(test)

    print("num results", len(x))

    count = 0
    for elem in x:
        print(elem)
        count += 1
        if count >= 1:
            break
'''

