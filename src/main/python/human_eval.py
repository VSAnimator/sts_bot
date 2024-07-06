import numpy as np
from openai_helpers import get_text_v3
from collections import OrderedDict
import ast
import dataset
from key_queries import similar_card_choice, campfire_choice, event_choice, pathing_choice, smithing_choice, boss_relic_choice

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
    #event_action = None
    #event_options = None
    smith_action = None
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
        '''
        if "Event" in action:
            event_action = action.split(":")[1].split(",")[0].strip().lower()
            event_options = [event_action] + action.split(":")[-1].strip().lower().split(", ")
            print("Event choice:", event_action, "Options:", event_options)
        '''
        if "Card smithed" in action:
            smith_action = action.split(":")[1].strip().lower()
            if smith_action not in smith_options:
                smith_options.append(smith_action)
            print("Smith action:", smith_action, "Options:", smith_options)
    return campfire_action, campfire_options, purge_action, purge_options, boss_relic_action, boss_relic_options, cards_action, cards_options, smith_action, smith_options

# Remove "actions taken" and "potions" from the sample state
#sample_state.pop('actions_taken', None)
#sample_state.pop('potions', None)

# Valid tests: 1. Campfire action, 2. Card purged in event/shop, 3. Boss relic, 4. Cards picked vs not, 5. Card smithed
valid_tests = ["Campfire action", "Card purged", "Boss relic", "Card picked", "Card smithed"]

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
        WHERE (actions_taken LIKE '%Campfire action%' or actions_taken LIKE '%Card smithed%')
        AND actions_taken NOT LIKE '%RECALL%'
        AND ascension_level = 20
        ORDER BY RANDOM()
        LIMIT 20
        """
    else:
        query = f"""
        SELECT * 
        FROM states
        WHERE actions_taken LIKE '%{test_type}%'
        AND ascension_level = 20
        ORDER BY RANDOM()
        LIMIT 20
        """

    # Execute the query
    result = db.query(query)

    #print(result)

    count = 0
    correct_count = 0
    best_actions = []
    chosen_actions = []
    random_accuracy = []
    for state in result:
        #print(state)
        #continue
        campfire_action, campfire_options, purge_action, purge_options, boss_relic_action, boss_relic_options, cards_action, cards_options, smith_action, smith_options = action_parser(state)
        screen_type = None
        similar_states = None
        # Filter to action, options for the test type
        if test_type == "Campfire action":
            action, options = campfire_action, campfire_options
            state['choice_list'] = options
            _, _, similar_states = campfire_choice(state, False)
            screen_type = "REST"
        elif test_type == "Card purged":
            action, options = purge_action, purge_options
            screen_type = "PURGE"
        elif test_type == "Boss relic":
            action, options = boss_relic_action, boss_relic_options
            state['choice_list'] = options
            _, _, similar_states = boss_relic_choice(state, False)
            screen_type = "BOSS_REWARD"
        elif test_type == "Card picked":
            action, options = cards_action, cards_options
            state['choice_list'] = options
            _, _, similar_states = similar_card_choice(state, False)
            screen_type = "CARD_REWARD"
        elif test_type == "Card smithed":
            action, options = smith_action, smith_options
            state['choice_list'] = options
            _, _, similar_states = smithing_choice(state, False)
            screen_type = "REST"

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
            similar_states = similar_states[:5]

        # Test system
        chosen_action = get_text_v3(state, "test_" + test_type + "_v1", similar_states, True)

        if chosen_action == action:
            correct_count += 1
        count += 1
        best_actions.append(action)
        chosen_actions.append(chosen_action)
        random_accuracy.append(1/len(options))
    #exit()
    print(f"Test type: {test_type}, Accuracy: {correct_count}/{count}", correct_count/count)
    print("Best actions:", best_actions)
    print("Chosen actions:", chosen_actions)
    print("Random accuracy:", np.mean(random_accuracy))

    # Write the results to a file
    with open("human_eval_" + test_type + "_results.txt", "w") as f:
        f.write(f"Test results: {correct_count}/{count}\n")
        f.write(f"Best actions: {best_actions}\n")
        f.write(f"Chosen actions: {chosen_actions}\n")
        f.write(f"Random accuracy: {np.mean(random_accuracy)}\n")
    return

if __name__ == "__main__":
    #test_results = run_test("Campfire action")
    #run_test("Card purged")
    run_test("Boss relic")
    #run_test("Card picked")
    #run_test("Card smithed")