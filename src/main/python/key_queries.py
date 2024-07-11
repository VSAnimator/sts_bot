import dataset
import json
from collections import Counter
import numpy as np
from wiki_info import get_card_rarity_by_name, get_relic_rarity_by_name

# Define the current game state for comparison
'''
current_state = {
    'deck': ['Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Strike_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Defend_R_upg0', 'Bash_upg0'],
    'relics': ['Burning Blood'],
    'potions': ['Weak Potion', 'Potion Slot', 'Potion Slot'],
    'current_hp': 80,
    'max_hp': 80,
    'floor': 40,
    'ascension_level': 0,
    'choice_list': ['carnage', 'ghostly armor', 'fire breathing']
}
'''

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
    #print("Current deck:", current_deck)
    #print("Target deck:", target_deck)
    deck_similarity = sum((current_deck & target_deck).values()) / max(sum(target_deck.values()), sum(current_deck.values()))
    similarity += deck_similarity * 100
    #print("Deck similarity:", deck_similarity)

    # Calculate similarity for relics
    current_relics = set(json.loads(state['relics']))
    target_relics = set(current_state['relics'])
    relics_similarity = len(current_relics & target_relics) / len(target_relics)
    similarity += relics_similarity * 100
    #print("Relics similarity:", relics_similarity)

    return similarity

# Assuming these functions are defined elsewhere in your code
def get_card_weight_by_rarity(card_name):
    # Dummy function: replace with actual implementation
    rarities = {'basic': 1, 'common': 1, 'uncommon': 3, 'rare': 5}
    return rarities.get(card_name.lower(), 1)

def get_relic_weight_by_rarity(relic_name):
    # Dummy function: replace with actual implementation
    rarities = {'common': 1, 'uncommon': 3, 'rare': 5, 'starter': 10, 'boss': 10, 'shop': 5}
    return rarities.get(relic_name.lower(), 1)

'''
def calculate_similarity(state, current_state):
    # Calculate similarity score based on attributes
    similarity = 0
    similarity += 100 - abs(state['current_hp'] - current_state['current_hp'])
    similarity += 100 - abs(state['max_hp'] - current_state['max_hp'])
    similarity += 100 - abs(state['floor'] - current_state['floor'])
    similarity += 100 - abs(state['ascension_level'] - current_state['ascension_level'])

    # Calculate similarity for deck
    current_deck = Counter(json.loads(state['deck']))
    target_deck = Counter([card.replace("_upg0", "").replace("_upg1", "+") for card in current_state['deck']])

    deck_similarity = 0
    total_weight = 0
    for card in target_deck:
        card_rarity = get_card_rarity_by_name(card)
        card_rarity = get_card_weight_by_rarity(card_rarity)
        common_cards = min(current_deck[card], target_deck[card])
        deck_similarity += common_cards * card_rarity
        total_weight += target_deck[card] * card_rarity

    deck_similarity = deck_similarity / total_weight if total_weight != 0 else 0
    similarity += deck_similarity * 50

    # Repeat in other direction
    reverse_deck_similarity = 0
    total_weight = 0
    for card in current_deck:
        card_rarity = get_card_rarity_by_name(card)
        card_rarity = get_card_weight_by_rarity(card_rarity)
        common_cards = min(current_deck[card], target_deck[card])
        reverse_deck_similarity += common_cards * card_rarity
        total_weight += current_deck[card] * card_rarity

    reverse_deck_similarity = reverse_deck_similarity / total_weight if total_weight != 0 else 0
    similarity += reverse_deck_similarity * 50

    #print("Deck similarity:", 0.5*deck_similarity + 0.5*reverse_deck_similarity)

    # Calculate similarity for relics
    current_relics = set(json.loads(state['relics']))
    target_relics = set(current_state['relics'])

    relics_similarity = 0
    total_weight = 0
    for relic in target_relics:
        relic_rarity = get_relic_rarity_by_name(relic)
        relic_rarity = get_relic_weight_by_rarity(relic_rarity)
        if relic in current_relics:
            relics_similarity += relic_rarity
        total_weight += relic_rarity

    relics_similarity = relics_similarity / total_weight if total_weight != 0 else 0

    # Repeat in other direction
    reverse_relics_similarity = 0
    total_weight = 0
    for relic in current_relics:
        relic_rarity = get_relic_rarity_by_name(relic)
        relic_rarity = get_relic_weight_by_rarity(relic_rarity)
        if relic in target_relics:
            reverse_relics_similarity += relic_rarity
        total_weight += relic_rarity

    reverse_relics_similarity = reverse_relics_similarity / total_weight if total_weight != 0 else 0

    #print("Relics similarity:", 0.5*relics_similarity + 0.5*reverse_relics_similarity)

    similarity += relics_similarity * 50 + reverse_relics_similarity * 50

    return similarity
'''

# Can make this more intelligent later
def similar_card_choice(current_state, max_action):
    print("Current state:", current_state)

    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    current_choice_list = current_state['choice_list']

    # If a + is in the choice, replace with "+1"
    # TODO: check this logic when running agent again
    # This is just for human eval...
    '''
    needs_replace = False
    for elem in current_choice_list:
        if "+" in elem and not elem.find("+1"):
            needs_replace = True

    if needs_replace:
        current_choice_list = [choice.replace("+", "+1") for choice in current_choice_list]
    '''
    print("Current choice list:", current_choice_list)
    current_choice_list = [choice.replace("+", "+1") for choice in current_choice_list]
    print("Current choice list:", current_choice_list)

    # Replace "bowl" with "singing bowl"
    current_choice_list = [choice.replace("bowl", "singing bowl") for choice in current_choice_list]

    # Adjust the SQL query to limit the number of rows returned and match similar action spaces
    # Has to have at least one element in common with the current_choice_list from actions_taken

    '''
    if len(current_choice_list) < 3:
        return "Not enough choices", True, None

    # Construct an array of all pairs of choices
    choice_pairs = []
    for elem1 in current_choice_list:
        for elem2 in current_choice_list:
            if elem1 != "skip" and elem2 != "skip" and elem1 != elem2:
                choice_pairs.append([elem1, elem2])
    '''

    choices_condition = " OR ".join(
        [f"actions_taken LIKE '%{choice}%'" for choice in current_choice_list if choice != 'skip']
        #[f"actions_taken LIKE '%{choice[0]}%{choice[1]}%'" for choice in choice_pairs]
    )

    query = f"""
    SELECT * 
    FROM states
    WHERE actions_taken LIKE '%Card picked%'
    AND ({choices_condition})
    AND floor BETWEEN {current_state['floor'] - 2} AND {current_state['floor'] + 2}
    AND ascension_level = {current_state['ascension_level']}
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        actions_taken = json.loads(state['actions_taken'])
        #print("Actions taken:", actions_taken)
        for action in actions_taken:
            if 'Card picked' in action:
                picked_info = action.split(", Cards not picked: ")
                if picked_info:
                    choice_list = [picked_info[0].split(": ")[1].lower()] + picked_info[1].lower().split(", ")
                    #print("Choice list:", choice_list)
                    #print("Current choice list:", current_choice_list)
                    if len(set(choice_list) & set(current_choice_list)) > 0:  # Check for at least one common card
                        similarity = calculate_similarity(state, current_state)
                        similar_states.append((similarity, state))

    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 5:
        return "Not enough similar states", True, None

    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 50 similar states
    top_similar_states = similar_states[:50]
    #print("Top similar states:", top_similar_states)
    #exit()

    # Calculate the ratio of times each card was picked to the total number of times it was available
    card_picked_counts = Counter()
    card_available_counts = Counter()

    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
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

                # If picked_card is not skip, increment the count for skip
                if picked_card != 'skip':
                    card_available_counts['skip'] += 1

    # Calculate the ratios
    print("Card picked counts:", card_picked_counts)
    print("Card available counts:", card_available_counts)
    card_ratios = {card: card_picked_counts[card] / card_available_counts[card] for card in card_available_counts}

    # Calculate the average similarity
    average_similarity = sum(similarity for similarity, _ in top_similar_states) / len(top_similar_states)

    # Filter card_ratios to only include cards in the current_choice_list
    card_ratios = {card: ratio for card, ratio in card_ratios.items() if card in current_choice_list or card == "skip"}

    # Add an option for "skip", with a ratio of 1 - sum(other ratios)
    #skip_ratio = max(1 - sum(card_ratios.values()), 0)
    #card_ratios['skip'] = skip_ratio

    print("Card ratios:", card_ratios)

    # Choose a card probabilistically, using the ratios as weights
    # First normalize the weights
    if max_action:
        best_card = max(card_ratios, key=card_ratios.get)
    else:
        total_weight = sum(card_ratios.values())
        card_ratios = {card: ratio / total_weight for card, ratio in card_ratios.items()}
        best_card = np.random.choice(list(card_ratios.keys()), p=list(card_ratios.values()))

    #best_card = max(card_ratios, key=card_ratios.get)

    # If "best_card" has a +1, replace with +
    best_card = best_card.replace("+1", "+")

    # Replace "singing bowl" with "bowl"
    best_card = best_card.replace("singing bowl", "bowl")

    # Turn into command
    command = f"choose {best_card}"

    # If skip is the best option, return "skip" command
    if best_card == "skip":
        command = "skip"
        if "singing bowl" in current_state['choice_list']:
            command = "choose bowl"
    
    return command, False, top_similar_states

# Can make this more intelligent later
def boss_relic_choice(current_state, max_action):
    print("Current state:", current_state)

    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    current_choice_list = current_state['choice_list']

    # Adjust the SQL query to limit the number of rows returned and match similar action spaces
    # Has to have at least one element in common with the current_choice_list from actions_taken
    # Modify "choice" to escape apostrophies
    # Escape single quotes in choices
    escaped_choices = [choice.replace("'", "''") for choice in current_choice_list]

    # Create the condition string
    choices_condition = " OR ".join(
        [f"actions_taken LIKE '%{choice}%'" for choice in escaped_choices]
    )

    query = f"""
    SELECT * 
    FROM states
    WHERE actions_taken LIKE '%Boss relic%'
    AND ({choices_condition})
    AND floor BETWEEN {current_state['floor'] - 2} AND {current_state['floor'] + 2}
    AND ascension_level = {current_state['ascension_level']}
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        actions_taken = json.loads(state['actions_taken'])
        #print("Actions taken:", actions_taken)
        for action in actions_taken:
            if 'Boss relic' in action:
                boss_relic_action = action.split(":")[1].split(",")[0].strip().lower()
                boss_relic_options = [boss_relic_action] + action.split(":")[-1].strip().lower().split(", ")
                if len(set(boss_relic_options) & set(current_choice_list)) > 0:  # Check for at least one common card
                    similarity = calculate_similarity(state, current_state)
                    similar_states.append((similarity, state))

    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 20:
        return "Not enough similar states", True, None

    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 50 similar states
    top_similar_states = similar_states[:50]

    # Calculate the ratio of times each card was picked to the total number of times it was available
    card_picked_counts = Counter()
    card_available_counts = Counter()

    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        actions_taken = json.loads(state['actions_taken'])
        for action in actions_taken:
            if 'Boss relic picked' in action:
                picked_info = action.split(", Boss relics not picked: ")
                picked_card = picked_info[0].split(": ")[1].lower()
                not_picked_cards = picked_info[1].lower().split(", ")

                # Increment the count for the picked card
                card_picked_counts[picked_card] += 1

                # Increment the count for all available cards
                for card in not_picked_cards:
                    card_available_counts[card] += 1
                card_available_counts[picked_card] += 1

                # If picked_card is not skip, increment the count for skip
                if picked_card != 'skip':
                    card_available_counts['skip'] += 1

    # Calculate the ratios
    print("Card picked counts:", card_picked_counts)
    print("Card available counts:", card_available_counts)
    card_ratios = {card: card_picked_counts[card] / card_available_counts[card] for card in card_available_counts}

    # Calculate the average similarity
    average_similarity = sum(similarity for similarity, _ in top_similar_states) / len(top_similar_states)

    # Filter card_ratios to only include cards in the current_choice_list
    card_ratios = {card: ratio for card, ratio in card_ratios.items() if card in current_choice_list or card == "skip"}

    # Add an option for "skip", with a ratio of 1 - sum(other ratios)
    #skip_ratio = max(1 - sum(card_ratios.values()), 0)
    #card_ratios['skip'] = skip_ratio

    print("Card ratios:", card_ratios)

    # Choose a card probabilistically, using the ratios as weights
    # First normalize the weights
    if max_action:
        best_card = max(card_ratios, key=card_ratios.get)
    else:
        total_weight = sum(card_ratios.values())
        card_ratios = {card: ratio / total_weight for card, ratio in card_ratios.items()}
        best_card = np.random.choice(list(card_ratios.keys()), p=list(card_ratios.values()))

    # Turn into command
    command = f"choose {best_card}"
    
    return command, False, top_similar_states

def campfire_choice(current_state, max_action):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    current_choice_list = current_state['choice_list']

    query = f"""
    SELECT * 
    FROM states
    WHERE (actions_taken LIKE '%Campfire%' OR actions_taken LIKE '%Smithed%')
    AND abs((current_hp * 1.0 / max_hp) - ({current_state['current_hp']} * 1.0 / {current_state['max_hp']})) < 0.1
    AND floor BETWEEN {current_state['floor'] - 1} AND {current_state['floor'] + 1}
    AND ascension_level = {current_state['ascension_level']}
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        similarity = calculate_similarity(state, current_state)
        similar_states.append((similarity, state))
        
    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 20:
        return "Not enough similar states", True, None
    
    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 20 similar states
    top_similar_states = similar_states[:20]

    # Compute the probability of each campfire action
    campfire_actions = Counter()
    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        actions_taken = json.loads(state['actions_taken'])
        for action in actions_taken:
            if 'Campfire action' in action:
                campfire_action = action.split(": ")[1].lower()
                campfire_actions[campfire_action] += 1
            else:
                campfire_action = "smith"
                campfire_actions[campfire_action] += 1

    # Filter out actions that are not in the current choice list
    print("Unfiltered campfire actions", campfire_actions)
    print("Choice list", current_choice_list)
    campfire_actions = {action: count for action, count in campfire_actions.items() if action in current_choice_list}

    # Remove recall from the list
    if "recall" in campfire_actions:
        del campfire_actions["recall"]

    # Probability dist from counter
    total_actions = sum(campfire_actions.values())

    campfire_actions = {action: count / total_actions for action, count in campfire_actions.items()}
    print("Campfire actions:", campfire_actions)

    # Sample from dist for decision
    if max_action:
        best_action = max(campfire_actions, key=campfire_actions.get)
    else:
        best_action = np.random.choice(list(campfire_actions.keys()), p=list(campfire_actions.values()))

    # If the decision is smith, but dig is available, switch to dig
    if best_action == "smith":
        if "dig" in current_state['choice_list']:
            best_action = "dig"

    # If the decision is smith, but purge is available and you have strikes or curses, switch to purge
    if best_action == "smith":
        if "purge" in current_state['choice_list']:
            best_action = "purge"

    # Auto-rest conditions
    '''
    if "rest" in current_state['choice_list']:
        # Check if HP below 50% and rest is available
        #if current_state['current_hp'] <= current_state['max_hp'] / 2:
        #    best_action = "rest"
        if current_state['floor'] % 17 >= 15:
            best_action = "rest"
    '''

    # Turn into command
    command = f"choose {best_action}"
    
    return command, False, top_similar_states

def smithing_choice(current_state, max_action):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    current_choice_list = current_state['choice_list']

    # Let's leave this out of the query for now
    choices_condition = " OR ".join(
        [f"actions_taken LIKE '%{choice}%'" for choice in current_choice_list]
    )

    query = f"""
    SELECT * 
    FROM states
    WHERE actions_taken LIKE '%Smithed%'
    AND abs((current_hp * 1.0 / max_hp) - ({current_state['current_hp']} * 1.0 / {current_state['max_hp']})) < 0.1
    AND floor BETWEEN {current_state['floor'] - 1} AND {current_state['floor'] + 1}
    AND ascension_level = {current_state['ascension_level']}
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        similarity = calculate_similarity(state, current_state)
        similar_states.append((similarity, state))
        
    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 20:
        return "Not enough similar states", True, None
    
    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 20 similar states
    top_similar_states = similar_states[:50]

    return None, False, top_similar_states

    # Compute the probability of each campfire action
    campfire_actions = Counter()
    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        actions_taken = json.loads(state['actions_taken'])
        for action in actions_taken:
            if "Card smithed" in action:
                campfire_action = action.split(": ")[1].lower()
                campfire_actions[campfire_action] += 1

    # Filter out actions that are not in the current choice list
    print("Unfiltered campfire actions", campfire_actions)
    print("Choice list", current_choice_list)
    campfire_actions = {action: count for action, count in campfire_actions.items() if action in current_choice_list}

    # Probability dist from counter
    total_actions = sum(campfire_actions.values())

    campfire_actions = {action: count / total_actions for action, count in campfire_actions.items()}
    print("Smithing choices:", campfire_actions)

    # Sample from dist for decision
    if max_action:
        best_action = max(campfire_actions, key=campfire_actions.get)
    else:
        best_action = np.random.choice(list(campfire_actions.keys()), p=list(campfire_actions.values()))

    # Turn into command
    command = f"choose {best_action}"
    
    return command, False, top_similar_states

def event_choice(current_state, max_action):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    if 'choice_list' not in current_state:
        current_choice_list = None
    else:
        current_choice_list = current_state['choice_list']

    if 'screen_state' not in current_state:
        event_id = current_state['actions_taken'].split(',')[0].split(': ')[1]
    else:
        event_id = current_state['screen_state']['event_id']
    print("Event ID:", event_id)

    escaped_id = event_id.replace("'", "''")

    query = f"""
    SELECT * 
    FROM states
    WHERE actions_taken LIKE '%{event_id}%'
    AND actions_taken LIKE '%Event%'
    AND floor BETWEEN {current_state['floor'] - 3} AND {current_state['floor'] + 3}
    AND ascension_level = {current_state['ascension_level']}
    LIMIT 500
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        similarity = calculate_similarity(state, current_state)
        similar_states.append((similarity, state))
        
    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 10:
        return "Not enough similar states", True, None
    
    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 20 similar states
    top_similar_states = similar_states[:20]

    # Compute the probability of each event choice
    event_choices = Counter()
    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        actions_taken = json.loads(state['actions_taken'])
        for action in actions_taken:
            if 'Event' in action:
                event_choice = action.split(": ")[-1].lower()
                event_choices[event_choice] += 1

    print("Unfiltered event choices", event_choices)

    # Filter out actions that are not in the current choice list
    if current_choice_list is not None:
        event_choices = {action: count for action, count in event_choices.items() if action in current_choice_list}
    # Can relax this condition if just passing into GPT TODO

    # Probability dist from counter
    total_actions = sum(event_choices.values())

    event_choices = {action: count / total_actions for action, count in event_choices.items()}
    print("Event choices:", event_choices)

    if len(event_choices) == 0:
        return "No valid choices", True, None

    # Sample from dist for decision
    if max_action:
        best_action = max(event_choices, key=event_choices.get)
    else:
        best_action = np.random.choice(list(event_choices.keys()), p=list(event_choices.values()))

    # Turn into command
    command = f"choose {best_action}"
    
    return command, False, top_similar_states

def battle_hp_prediction(current_state, max_action):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Get the particular battle enemy from the state
    if 'screen_state' not in current_state:
        for action in json.loads(current_state['actions_taken']):
            if 'Battle:' in action:
                enemy_name = action.split(',')[1].split(': ')[1]
                continue
    else:
        enemy_name = current_state['screen_state']['enemy_name']

    #print("Enemy name:", enemy_name)

    # Now query the database for similar states
    query = f"""
    SELECT *
    FROM states
    WHERE actions_taken LIKE '%Battle:%' AND actions_taken LIKE '%{enemy_name}%'
    AND floor BETWEEN {current_state['floor'] - 1} AND {current_state['floor'] + 1}
    AND ascension_level = {current_state['ascension_level']}
    AND victory = 1
    LIMIT 500
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        #print("State:", state)
        similarity = calculate_similarity(state, current_state)
        similar_states.append((similarity, state))
    #exit()

    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 20:
        return "Not enough similar states", True, None
    
    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 20 similar states
    top_similar_states = similar_states[:20]

    # Compute the hp lost in each state
    hp_lost = Counter()
    turns = Counter()
    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        for action in json.loads(state['actions_taken']):
            if 'Battle:' in action:
                print("Action:", action)
                curr_hp_lost = (int)(float(action.split(",")[0].split(": ")[1].split(" ")[0]))
                curr_turns = (int)(float(action.split(": ")[-1].split(",")[0]))
        hp_lost[curr_hp_lost] += 1
        turns[curr_turns] += 1
    
    # Get avg hp lost from counter
    total_hp_lost = sum([int(hp) * count for hp, count in hp_lost.items()])
    total_count = sum(hp_lost.values())
    avg_hp_lost = total_hp_lost / total_count
    avg_turns = sum([int(turn) * count for turn, count in turns.items()]) / sum(turns.values())

    return avg_hp_lost, avg_turns, top_similar_states

def pathing_choice(current_state, max_action):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    # Serialize lists to JSON strings for comparison
    current_choice_list = current_state['choice_list']

    # Also get the extended pathing options
    extended_next_nodes = current_state['screen_state']['expanded_next_nodes']

    # Now query the database for similar states
    query = f"""
    SELECT *
    FROM states
    WHERE actions_taken LIKE '%Path taken%'
    AND floor BETWEEN {current_state['floor'] - 1} AND {current_state['floor'] + 1}
    AND ascension_level = {current_state['ascension_level']}
    LIMIT 500
    """

    # Execute the query
    result = db.query(query)

    # Find similar states
    similar_states = []
    for state in result:
        similarity = calculate_similarity(state, current_state)
        similar_states.append((similarity, state))

    # If there are fewer than 20 similar states, return
    print("Number of similar states:", len(similar_states))
    if len(similar_states) < 20:
        return "Not enough similar states", True, None
    
    # Sort by similarity
    similar_states.sort(reverse=True, key=lambda x: x[0])

    # Limit to top 20 similar states
    top_similar_states = similar_states[:20]

    # For each observed pathing choice, compare to the extended_next_nodes options
    path_choices = Counter()
    for _, state in top_similar_states:
        if "id" in current_state and state['id'] == current_state['id']:
            continue
        actions_taken = json.loads(state['actions_taken'])
        for action in actions_taken:
            if 'Path taken' in action:
                path_taken = action.split(": ")[1].lower()
                # Now match path_taken to the extended_next_nodes
                # Most similar string wins as long as one has nonzero similarity
                # Crop both strings to the length of the smaller one, and check percentage tokens in common
                max_similarity = 0
                best_path = ""
                print("Path taken:", path_taken)
                for path_option, path_symbols in extended_next_nodes.items():
                    # Crop path_symbols and path_taken to the length of the smaller one
                    min_length = min(len(path_symbols), len(path_taken))
                    cropped_path_symbols = path_symbols[:min_length].lower()
                    cropped_path_taken = path_taken[:min_length]
                    print("Cropped path symbols", cropped_path_symbols)
                    similarity = sum([1 for i in range(min_length) if cropped_path_symbols[i] == cropped_path_taken[i]]) / min_length
                    print("Similarity:", similarity)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_path = path_option
                path_choices[best_path] += 1

    # Probability dist from counter
    total_actions = sum(path_choices.values())

    path_choices = {action: count / total_actions for action, count in path_choices.items()}
    print("Path choices:", path_choices)

    # Sample from dist for decision
    if max_action:
        best_action = max(path_choices, key=path_choices.get)
    else:
        best_action = np.random.choice(list(path_choices.keys()), p=list(path_choices.values()))

    # If best_action is an empty string, default to gpt
    if best_action == "":
        return "gpt", True, None

    # Turn into command
    command = f"choose {best_action}"

    return command, False, top_similar_states

# Test a query
#command, done = similar_card_choice(current_state, False)