import dataset
import json
from collections import Counter
import numpy as np
import random
from openai_helpers import state_comparison
import ast

# Query a random state from the database
def query_random_state(victory, floor=None):
    db_url = 'sqlite:///mydatabase.db'
    # Connect to your SQLite database
    db = dataset.connect(db_url)

    # Specify your table name
    table_name = 'states'

    # Get the table
    table = db[table_name]

    # Count the number of rows in the table
    row_count = table.count()

    # Generate a random offset
    #random_offset = random.randint(0, row_count - 1)

    # Fetch the random row using a query with LIMIT and OFFSET
    if floor is None:
        query = f'SELECT states.*, runs.victory FROM {table_name}, runs WHERE states.run_id = runs.id and ascension_level=10 and victory={victory} and game_state_floor > 10 and game_state_floor < 45 ORDER BY RANDOM() LIMIT 1'
    else:
        query = f'SELECT states.*, runs.victory FROM {table_name}, runs WHERE states.run_id = runs.id and ascension_level=10 and victory={victory} and game_state_floor={floor} ORDER BY RANDOM() LIMIT 1'
    result = db.query(query)

    # Get the random row
    random_row = next(result)

    return random_row

def clean_state(curr_state):
    # I want to keep the following keys: 'game_state_deck', 'game_state_relics', 'game_state_gold', 'game_state_potions', 'game_state_current_hp', 'game_state_max_hp'
    return {
        'floor': curr_state['game_state_floor'],
        'ascension_level': curr_state['game_state_ascension_level'],
        'deck': curr_state['game_state_deck'],
        'relics': curr_state['game_state_relics'],
        'gold': curr_state['game_state_gold'],
        'potions': curr_state['game_state_potions'],
        'current_hp': curr_state['game_state_current_hp'],
        'max_hp': curr_state['game_state_max_hp']
    }

db_url = 'sqlite:///mydatabase.db'
db = dataset.connect(db_url)
table = db['states']

nn_mode = False
comparison_mode = True
system_prompt = "You are a superhuman AI evaluating the relative win probability of two states from two different playthrough of Slay the Spire. Evaluate the current decks and relics in the context of the current game states along the following dimensions: hp, attack, defense, scaling, synergies, card draw. Evaluate which of the two states will perform better. Output 1 if state 1 is better, or -1 if state 2 is better. Think step by step."
need_similar_states = False
if nn_mode:
    need_similar_states = True
# Generate random hex run id
run_id = random.randint(0, 1000000)
losses = []
preds = []
gts = []
for i in range(20):
    # Randomly generate 0/1 for victory_query
    victory_query = random.randint(0, 1)
    state1 = query_random_state(victory_query)
    state2 = query_random_state(1 - victory_query, state1['game_state_floor'])

    #print("State 1: ", state1)
    #print("State 2: ", state2)

    # Comparison is 1 if state1 is better, -1 if state2 is better, 0 if they are roughly equal
    gt_val = 1 if state1['victory'] > state2['victory'] else -1 if state2['victory'] > state1['victory'] else 0
    
    print("Ground truth value: ", gt_val)
    state1 = clean_state(state1)
    state2 = clean_state(state2)

    print("State 1 cleaned: ", state1)
    print("State 2 cleaned: ", state2)

    # Now we have two states to compare
    system_prompt, llm_pred = state_comparison(system_prompt, state1, state2, run_id)

    try:
        pred_victory = (int)(llm_pred['predicted_outcome'])
        losses.append(np.abs(pred_victory - gt_val))
        preds.append(pred_victory)
        gts.append(gt_val)

        if pred_victory == gt_val:
            print("Correct")
            continue

        '''
        # Now update system prompt
        x = update_state_comparison_prompt(system_prompt, state1, state2, str(llm_pred), ("Correct, " if pred_victory == gt_val else "Incorrect, ") + "the " + ("first" if gt_val == 1 else "second") + " state is better", run_id)

        try:
            try:
                x = ast.literal_eval(x)
            except:
                try:
                    x = json.loads(x)
                except:
                    try:
                        x = json.loads(x.replace("'", "\""))
                    except:
                        x = eval(x)
            #x = json.loads(x)

            # Check if "new_prompt" in x
            if "new_prompt" in x:
                system_prompt = x['new_prompt']
        except Exception as e:
            print("Error: ", e)
        '''
    except Exception as e:
        print("Error 2: ", e)

    print("Losses: ", losses)
    print("Mean loss: ", np.mean(losses))
    print("Max loss: ", np.max(losses))
    print("Min loss: ", np.min(losses))
    print("Preds: ", preds)
    print("Gts: ", gts)




