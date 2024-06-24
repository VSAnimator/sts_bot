import dataset
import json
from collections import Counter

# Connect to the database
db_url = 'sqlite:///slay_the_spire.db'
db = dataset.connect(db_url)
table = db['states']

# Define the current game state for comparison
current_state = {
    'deck': ['Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0'],
    'relics': ['Burning Blood'],
    'potions': ['Weak Potion', 'Potion Slot', 'Potion Slot'],
    'current_hp': 80,
    'max_hp': 80,
    'floor': 1,
    'ascension_level': 0,
    'choice_list': ['carnage', 'ghostly armor', 'fire breathing']
}

def calculate_similarity(state, current_state):
    # Calculate similarity score based on attributes
    similarity = 0
    similarity += 100 - abs(state['current_hp'] - current_state['current_hp'])
    similarity += 100 - abs(state['max_hp'] - current_state['max_hp'])
    similarity += 100 - abs(state['floor'] - current_state['floor'])
    similarity += 100 - abs(state['ascension_level'] - current_state['ascension_level'])

    # Calculate similarity for deck
    current_deck = Counter(json.loads(state['deck']))
    # In target deck, replace _upg0 with "" and _upg1 with "+" to match current deck format
    target_deck = Counter([card.replace("_upg0", "").replace("_upg1", "+") for card in current_state['deck']])
    print("Current deck:", current_deck)
    print("Target deck:", target_deck)
    deck_similarity = sum((current_deck & target_deck).values()) / max(sum(target_deck.values()), sum(current_deck.values()))
    similarity += deck_similarity * 100
    print("Deck similarity:", deck_similarity)

    # Calculate similarity for relics
    current_relics = set(json.loads(state['relics']))
    target_relics = set(current_state['relics'])
    relics_similarity = len(current_relics & target_relics) / len(target_relics)
    similarity += relics_similarity * 100
    print("Relics similarity:", relics_similarity)

    return similarity

# Serialize lists to JSON strings for comparison
current_choice_list = current_state['choice_list']

# Adjust the SQL query to count the number of similar states
count_query = f"""
SELECT COUNT(*) as count
FROM states
WHERE actions_taken LIKE '%Card picked%'
AND (
    actions_taken LIKE '%Carnage%'
    OR actions_taken LIKE '%Ghostly Armor%'
    OR actions_taken LIKE '%Fire Breathing%'
)
AND floor BETWEEN {current_state['floor'] - 2} AND {current_state['floor'] + 2}
AND ascension_level = {current_state['ascension_level']}
"""

# Execute the count query
count_result = db.query(count_query)
count = next(count_result)['count']
print(f"Number of similar states: {count}")
#exit()

# Adjust the SQL query to limit the number of rows returned and match similar action spaces
query = f"""
SELECT * 
FROM states
WHERE actions_taken LIKE '%Card picked%'
AND (
    actions_taken LIKE '%Carnage%'
    OR actions_taken LIKE '%Ghostly Armor%'
    OR actions_taken LIKE '%Fire Breathing%'
)
AND floor BETWEEN {current_state['floor'] - 2} AND {current_state['floor'] + 2}
AND ascension_level = {current_state['ascension_level']}
"""

# Execute the query
result = db.query(query)

# Find similar states
similar_states = []
for state in result:
    actions_taken = json.loads(state['actions_taken'])
    print("Actions taken:", actions_taken)
    for action in actions_taken:
        if 'Card picked' in action:
            picked_info = action.split(", Cards not picked: ")
            if picked_info:
                choice_list = [picked_info[0].split(": ")[1].lower()] + picked_info[1].lower().split(", ")
                print("Choice list:", choice_list)
                print("Current choice list:", current_choice_list)
                if len(set(choice_list) & set(current_choice_list)) > 0:  # Check for at least one common card
                    similarity = calculate_similarity(state, current_state)
                    similar_states.append((similarity, state))

# Sort by similarity
similar_states.sort(reverse=True, key=lambda x: x[0])

# Limit to top 20 similar states
top_similar_states = similar_states[:20]

# Calculate the ratio of times each card was picked to the total number of times it was available
card_picked_counts = Counter()
card_available_counts = Counter()

for _, state in top_similar_states:
    actions_taken = json.loads(state['actions_taken'])
    for action in actions_taken:
        if 'Card picked' in action:
            picked_info = action.split(", Cards not picked: ")
            picked_card = picked_info[0].split(": ")[1].lower()
            not_picked_cards = picked_info[1].lower().split(", ")

            # Increment the count for the picked card
            card_picked_counts[picked_card] += 1

            # Increment the count for all available cards
            for card in not_picked_cards:
                card_available_counts[card] += 1
            card_available_counts[picked_card] += 1

# Calculate the ratios
card_ratios = {card: card_picked_counts[card] / card_available_counts[card] for card in card_available_counts}

# Calculate the average similarity
average_similarity = sum(similarity for similarity, _ in top_similar_states) / len(top_similar_states)

# Print the ratios and average similarity
print("Card Ratios (Picked/Available):")
for card, ratio in card_ratios.items():
    print(f"{card}: {ratio:.2f}")

print(f"\nAverage Similarity: {average_similarity:.2f}")
