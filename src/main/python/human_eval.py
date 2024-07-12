import numpy as np
from openai_helpers import get_text_v3
from collections import OrderedDict
import ast
import dataset
from key_queries import similar_card_choice, campfire_choice, event_choice, pathing_choice, smithing_choice, boss_relic_choice, battle_hp_prediction
import json

# This script will select random states from winning runs, find the decisions made by humans, and see if GPT can make similar decisions

# Get the following: 1. Campfire action, 2. Card purged in event/shop, 3. Boss relic, 4. Cards picked vs not, 5. Event choice
def action_parser(sample_state):
    actions_taken = ast.literal_eval(sample_state['actions_taken'])
    campfire_action = None
    campfire_options = ["rest", "smith"]
    purge_action = None
    purge_options = ast.literal_eval(sample_state['deck'])
    purge_options = [elem.lower() for elem in purge_options]
    # Remove Ascender's bane from purge_options
    if "AscendersBane" in purge_options:
        purge_options.remove("AscendersBane")
    boss_relic_action = None
    boss_relic_options = None
    cards_action = None
    cards_options = None
    event_name = None
    event_action = None
    smith_action = None
    battle_hp_lost = None
    battle_turns = None
    smith_options = list(set(ast.literal_eval(sample_state['deck'])))
    if "AscendersBane" in smith_options:
        smith_options.remove("AscendersBane")
    smith_options = [card.lower() for card in smith_options if "+1" not in card or "Searing Blow" in card]
    print("Actions taken:", actions_taken)
    for action in actions_taken:
        # Check for campfire action
        if "Campfire action" in action or "Card smithed" in action:
            if "Card smithed" in action:
                campfire_action = "smith"
            else:
                campfire_action = action.split(":")[1].strip().lower()
            if campfire_action not in campfire_options:
                campfire_options.append(campfire_action)
            print("Campfire action:", campfire_action, "Options:", campfire_options)
        # Check for card purged
        if "Card purged" in action:
            purge_action = action.split(":")[1].strip().lower()
            if purge_action not in purge_options:
                purge_options.append(purge_action)
            print("Purge action:", purge_action, "Options:", purge_options)
        # Check for boss relic
        if "Boss relic" in action:
            # Format: Boss relic picked: {picked_relic}, Boss relics not picked: {not_picked_relics}
            boss_relic_action = action.split(":")[1].split(",")[0].strip().lower()
            boss_relic_options = [boss_relic_action] + action.split(":")[-1].strip().lower().split(", ")
            print("Boss relic:", boss_relic_action, "Options:", boss_relic_options)
        # Check for cards picked
        if "Card picked" in action:
            cards_action = action.split(":")[1].split(",")[0].strip().lower()
            cards_options = [cards_action] + action.split(":")[-1].strip().lower().split(", ")
            # Add "skip" if not there
            if "skip" not in cards_options:
                cards_options.append("skip")
            print("Cards picked:", cards_action, "Options:", cards_options)
        # Check for event choice
        if "Event" in action:
            event_name = action.split(":")[1].split(",")[0].strip().lower()
            event_action = action.split(":")[-1].strip().lower()
            print("Event:", event_name, "Action:", event_action)
        if "Card smithed" in action:
            smith_action = action.split(":")[1].strip().lower()
            if smith_action not in smith_options:
                smith_options.append(smith_action)
            print("Smith action:", smith_action, "Options:", smith_options)
        if "Battle:" in action:
            battle_hp_lost = (int)(float(action.split(",")[0].split(": ")[1].split(" ")[0]))
            battle_turns = (int)(float(action.split(": ")[-1].split(",")[0]))
            print("Battle HP lost:", battle_hp_lost)
            print("Battle turns:", battle_turns)
    return campfire_action, campfire_options, purge_action, purge_options, boss_relic_action, boss_relic_options, cards_action, cards_options, smith_action, smith_options, event_name, event_action, battle_hp_lost, battle_turns

# Remove "actions taken" and "potions" from the sample state
#sample_state.pop('actions_taken', None)
#sample_state.pop('potions', None)

# Valid tests: 1. Campfire action, 2. Card purged in event/shop, 3. Boss relic, 4. Cards picked vs not, 5. Card smithed
valid_tests = ["Campfire action", "Card purged", "Boss relic", "Card picked", "Card smithed", "Event", "Battle"]

'''
def ss_prob(similar_states, options):
    # Go through similar states, find one that is in options
    for elem in similar_states:
        actions_taken = json.loads(elem['actions_taken'])
        for action in actions_taken:
            action = action.lower()
            print(action)
            for option in options:
                print(option)
                print(action.find(options))
                if action.find(option):
                    print("Success")
                    exit()
                    return option
    return None
'''

def run_test(test_type):
    if test_type not in valid_tests:
        print(f"Invalid test type: {test_type}")
        return
    
    # Let's test this by querying the sqlite database for actions of each type
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    if test_type == "Campfire action":
        query = f"""
        SELECT *
        FROM states
        WHERE (actions_taken LIKE '%Card smithed%')
        AND actions_taken NOT LIKE '%RECALL%'
        AND ascension_level = 20
        AND victory = 1
        ORDER BY RANDOM()
        LIMIT 50
        """
        # or actions_taken LIKE '%Card smithed%') (actions_taken LIKE '%Campfire action%')
    else:
        query_string = test_type
        if test_type == "Battle":
            query_string = "Battle:"
        query = f"""
        SELECT * 
        FROM states
        WHERE actions_taken LIKE '%{query_string}%' and actions_taken NOT LIKE '%Neow Event%'
        AND ascension_level = 20
        AND victory = 1
        ORDER BY RANDOM()
        LIMIT 50
        """
        #AND actions_taken LIKE '%skip%'

    # Execute the query
    result = db.query(query)

    #print(result)

    count = 0
    correct_count = 0
    best_actions = []
    chosen_actions = []
    random_accuracy = []
    hp_pred_error = []
    turns_pred_error = []
    for state in result:
        print(state)
        #continue
        campfire_action, campfire_options, purge_action, purge_options, boss_relic_action, boss_relic_options, cards_action, cards_options, smith_action, smith_options, event_name, event_action, battle_hp_lost, battle_turns = action_parser(state)
        screen_type = None
        similar_states = None
        action = None
        options = None
        ss_choice = None
        # Filter to action, options for the test type
        if test_type == "Campfire action":
            action, options = campfire_action, campfire_options
            state['choice_list'] = options
            ss_choice, _, similar_states = campfire_choice(state, False)
            screen_type = "REST"
        elif test_type == "Card purged":
            action, options = purge_action, purge_options
            screen_type = "PURGE"
        elif test_type == "Boss relic":
            action, options = boss_relic_action, boss_relic_options
            state['choice_list'] = options
            ss_choice, _, similar_states = boss_relic_choice(state, False)
            screen_type = "BOSS_REWARD"
        elif test_type == "Card picked":
            action, options = cards_action, cards_options
            state['choice_list'] = options
            ss_choice, _, similar_states = similar_card_choice(state, True)
            screen_type = "CARD_REWARD"
        elif test_type == "Card smithed":
            action, options = smith_action, smith_options
            state['choice_list'] = options
            _, _, similar_states = smithing_choice(state, False)
            screen_type = "REST"
        elif test_type == "Event":
            options = None
            action = event_action
            print("Event options:", options)
            print("State:", state)
            print("Action", action)
            ss_choice, _, similar_states = event_choice(state, False)
            print("SS choice:", ss_choice)
            screen_type = "EVENT"
        elif test_type == "Battle":
            ss_battle_hp, ss_turns, similar_states = battle_hp_prediction(state, False)
            if similar_states is None:
                continue
            screen_type = "BATTLE"

        state.pop('actions_taken', None)
        state.pop('potions', None)

        # Stick in the action and options
        #state[test_type] = action
        state["screen_type"] = screen_type
        state["available_commands"] = options
        state["act"] = ((int)(state["floor"] / 17) + 1)
        
        # If similar states is not None, filter out anything with the same id
        if similar_states:
            similar_states = [s[1] for s in similar_states if s[1]['id'] != state['id']]

        # Test nearest neighbors system
        test_nn = True
        if test_nn:
            chosen_action = ss_choice
            if chosen_action is not None and "choose " in chosen_action:
                chosen_action = chosen_action[7:]
            if chosen_action == "bowl":
                chosen_action = "singing bowl"
        else:
            if similar_states:
                similar_states = similar_states[:5]
            chosen_action = get_text_v3(state, "test_" + test_type + "_branched", similar_states, True)
        if chosen_action == action:
            correct_count += 1
        count += 1
        best_actions.append(action)
        chosen_actions.append(chosen_action)
        if options:
            random_accuracy.append(1/len(options))
        if test_type == "Battle":
            hp_pred_error.append(abs(battle_hp_lost - ss_battle_hp))
            turns_pred_error.append(abs(battle_turns - ss_turns))
            print("Battle HP prediction:", ss_battle_hp, "Actual:", battle_hp_lost)
    #exit()
    print(f"Test type: {test_type}, Accuracy: {correct_count}/{count}", correct_count/count)
    print("Best actions:", best_actions)
    print("Chosen actions:", chosen_actions)
    print("Random accuracy:", np.mean(random_accuracy))
    if test_type == "Battle":
        print("HP prediction error:", np.mean(hp_pred_error))
        print("Turns prediction error:", np.mean(turns_pred_error))

    # Write the results to a file
    with open("human_eval_" + test_type + "_results.txt", "w") as f:
        f.write(f"Test results: {correct_count}/{count}\n")
        f.write(f"Best actions: {best_actions}\n")
        f.write(f"Chosen actions: {chosen_actions}\n")
        f.write(f"Random accuracy: {np.mean(random_accuracy)}\n")
        if test_type == "Battle":
            f.write(f"HP prediction error: {np.mean(hp_pred_error)}\n")
            f.write(f"Turns prediction error: {np.mean(turns_pred_error)}\n")
            f.write(f"HP prediction error list: {hp_pred_error}\n")
            f.write(f"Turns prediction error list: {turns_pred_error}\n")
    return

if __name__ == "__main__":
    #run_test("Campfire action")
    #run_test("Card purged")
    #run_test("Boss relic")
    run_test("Card picked")
    #run_test("Event")
    #run_test("Battle")
    #run_test("Card smithed")