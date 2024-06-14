import json
from collections import Counter

# Will have to add something to note when cards/potions generate new cards that can then be played
# Similarly for potions played, etc. should keep a record of actions. 
def extract_battle_info(log):
    # Extract player health change
    initial_health = log[0]['player_state']['current_health']
    final_health = log[-1]['player_state']['current_health']
    health_change = final_health - initial_health
    
    # Extract cards played and their counts
    cards_played = [entry['card_name'] for entry in log]
    card_counts = Counter(cards_played)
    
    return health_change, card_counts

'''
# Sample log provided
battle_log = [
    {"card_name": "Defend", "card_index": 1, "player_state": {"max_health": 80, "current_health": 72}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 13}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 0, "player_state": {"max_health": 80, "current_health": 72}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 13}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Defend", "card_index": 2, "player_state": {"max_health": 80, "current_health": 72}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 7}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Defend", "card_index": 2, "player_state": {"max_health": 80, "current_health": 68}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 7}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 0, "player_state": {"max_health": 80, "current_health": 68}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 7}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 0, "player_state": {"max_health": 80, "current_health": 68}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 1}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Defend", "card_index": 0, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Defend", "card_index": 0, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Defend", "card_index": 0, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 34}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 28}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 22}]},
    {"card_name": "Defend", "card_index": 2, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 16}]},
    {"card_name": "Defend", "card_index": 2, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 16}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 65}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 16}]},
    {"card_name": "Bash", "card_index": 0, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 63}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 12}]},
    {"card_name": "Strike", "card_index": 1, "monster_index": 1, "player_state": {"max_health": 80, "current_health": 63}, "monster_state": [{"monster_index": 0, "monster_name": "Spike Slime (S)", "max_hp": 13, "current_hp": 0}, {"monster_index": 1, "monster_name": "Acid Slime (M)", "max_hp": 34, "current_hp": 4}]}
]

# Analyze the log
health_change, card_counts = extract_battle_info(battle_log)
print(f'Player Health Change: {health_change}')
print(f'Cards Played: {card_counts}')
'''