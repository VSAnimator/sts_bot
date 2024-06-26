import json
import dataset

def process_event(event, play_id):
    # Initialize state variables
    current_deck = ["Strike_R", "Strike_R", "Strike_R", "Strike_R", "Strike_R", "Defend_R", "Defend_R", "Defend_R", "Defend_R", "Bash"]
    current_relics = ["Burning Blood"]
    current_potions = []
    ascension_level = event.get("ascension_level", 0)
    print("Ascension level: ", ascension_level)

    # Unroll trajectory information
    states = []

    # Add the initial state with the Neow bonus
    try:
        states.append({
            "play_id": play_id,
            "floor": 0,
            "deck": json.dumps(current_deck.copy()),
            "relics": json.dumps(current_relics.copy()),
            "potions": json.dumps(current_potions.copy()),
            "current_hp": event["current_hp_per_floor"][0] if event["current_hp_per_floor"] else 0,
            "max_hp": event["max_hp_per_floor"][0] if event["max_hp_per_floor"] else 0,
            "actions_taken": json.dumps([f"Neow Event: {event['neow_bonus']}"]),
            "ascension_level": ascension_level
        })
    except Exception as e:
        print("Error in initial state")
        print("Event: ", event)

    for floor in range(0, event["floor_reached"]):
        if floor >= 50:
            break
        try:
            hp_floor = max(0, floor - 1)
            state = {
                "play_id": play_id,
                "floor": floor,
                "deck": json.dumps(current_deck.copy()),
                "relics": json.dumps(current_relics.copy()),
                "potions": json.dumps(current_potions.copy()),
                "current_hp": event["current_hp_per_floor"][hp_floor],
                "max_hp": event["max_hp_per_floor"][hp_floor],
                "actions_taken": [],
                "ascension_level": ascension_level
            }
        except Exception as e:
            print("Error in floor: ", floor)
            print("Event: ", event)
            return states

        # Add card choices and purges
        for choice in event["card_choices"]:
            if choice["floor"] == floor:
                picked = choice["picked"]
                not_picked = choice["not_picked"]
                state["actions_taken"].append(f"Card picked: {picked}, Cards not picked: {', '.join(not_picked)}")
                if picked != "SKIP":
                    current_deck.append(picked)

        for event_choice in event["event_choices"]:
            if event_choice["floor"] == floor:
                state["actions_taken"].append(f"Event: {event_choice['event_name']}, Player choice: {event_choice['player_choice']}")
                if "cards_obtained" in event_choice:
                    current_deck.extend(event_choice["cards_obtained"])
                if "cards_removed" in event_choice:
                    for card in event_choice["cards_removed"]:
                        try:
                            current_deck.remove(card)
                        except Exception as e:
                            print("Current deck", current_deck)
                            print("Card not found in deck: ", card)

        for purge_floor, item_purged in zip(event["items_purged_floors"], event["items_purged"]):
            if purge_floor == floor:
                state["actions_taken"].append(f"Card purged: {item_purged}")
                try:
                    current_deck.remove(item_purged)
                except Exception as e:
                    print("Current deck", current_deck)
                    print("Card not found in deck: ", item_purged)

        for relic in event["relics_obtained"]:
            if relic["floor"] == floor:
                state["actions_taken"].append(f"Relic obtained: {relic['key']}")
                current_relics.append(relic["key"])

        for potion in event["potions_obtained"]:
            if potion["floor"] == floor:
                state["actions_taken"].append(f"Potion obtained: {potion['key']}")
                current_potions.append(potion["key"])

        # Handle campfire choices
        for campfire_choice in event["campfire_choices"]:
            if campfire_choice["floor"] == floor:
                if campfire_choice["key"] == "SMITH":
                    card_smithed = campfire_choice["data"]
                    # Upgrade the corresponding card in the deck
                    for i, card in enumerate(current_deck):
                        if card == card_smithed:
                            current_deck[i] = f"{card_smithed}+1"
                            break
                    state["actions_taken"].append(f"Card smithed: {card_smithed}")
                else:
                    state["actions_taken"].append(f"Campfire action: {campfire_choice['key']}")

        # Handle boss relics choices for floors 16 and 33
        if floor == 16 and len(event.get("boss_relics", [])) > 0:
            boss_relic_choice = event["boss_relics"][0]
            picked_relic = boss_relic_choice["picked"]
            not_picked_relics = boss_relic_choice["not_picked"]
            state["actions_taken"].append(f"Boss relic picked: {picked_relic}, Boss relics not picked: {', '.join(not_picked_relics)}")
            current_relics.append(picked_relic)

        if floor == 33 and len(event.get("boss_relics", [])) > 1:
            boss_relic_choice = event["boss_relics"][1]
            picked_relic = boss_relic_choice["picked"]
            not_picked_relics = boss_relic_choice["not_picked"]
            state["actions_taken"].append(f"Boss relic picked: {picked_relic}, Boss relics not picked: {', '.join(not_picked_relics)}")
            current_relics.append(picked_relic)

        # Add pathing decisions
        try:
            if floor <= len(event["path_per_floor"]):
                #print(floor)
                #print(event["path_per_floor"])
                #print(event["path_taken"])
                path = event["path_per_floor"][floor]
                # Want to include up to 3 steps of the path where possible
                #print("Path per floor: ", event["path_per_floor"])
                #print("path", path)
                if path is not None:
                    offset = 1
                    while floor + offset < len(event["path_per_floor"]) and len(path) < 3:
                        if event["path_per_floor"][floor + offset] is None:
                            break
                        path = path + event["path_per_floor"][floor + offset]
                        offset += 1
                        #print("Path: ", path)
                state["actions_taken"].append(f"Path taken: {path}")
                #if floor == 49:
                #    print("Path: ", path)
        except Exception as e:
            print("Error in pathing decisions")
            print("Event: ", event)
            print("Exception", e)
            print(floor)
            print(event["path_per_floor"])

        state["actions_taken"] = json.dumps(state["actions_taken"])
        states.append(state)
    return states

def process_json_file(json_file, db_url):
    state_count = 0
    trajectory_count = 0

    with open(json_file, 'r') as file:
        data = json.load(file)
    
    db = dataset.connect(db_url)
    table = db['states']
    
    for entry in data:
        event = entry["event"]
        play_id = event["play_id"]

        try:
            # Check if the playthrough was a winning run with Ironclad
            if event["character_chosen"] == "IRONCLAD" and event["victory"]:
                states = process_event(event, play_id)
                # Increment trajectory and state counts
                trajectory_count += 1
                state_count += len(states)
                print("Inserting ", len(states), " states")
                print("State count", state_count)
                print("Trajectory count", trajectory_count)
                table.insert_many(states)
        except Exception as e:
            print("Error in processing event")
            print("Event: ", event)
            print("Exception: ", e)

# Example usage
file_folder = '/Users/sarukkai/Downloads/Monthly_2020_11/'
#json_file = '/Users/sarukkai/Downloads/2020-11-11-13-26#1517.json'
# Loop through files in folder
import os
for filename in os.listdir(file_folder):
    if filename.endswith(".json"):
        json_file = file_folder + filename
        print("Processing file: ", json_file)
        db_url = 'sqlite:///slay_the_spire.db'
        process_json_file(json_file, db_url)
