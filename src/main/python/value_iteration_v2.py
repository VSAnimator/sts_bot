import dataset
import json
from collections import Counter
import numpy as np
import random
from openai_helpers import win_prediction, update_win_prediction_prompt
import ast

# Query a random state from the database
def query_random_state():
    db_url = 'sqlite:///slay_the_spire.db'
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
    query = f'SELECT * FROM {table_name} WHERE ascension_level=20 and floor=45 ORDER BY RANDOM() LIMIT 1'
    result = db.query(query)

    # Get the random row
    random_row = next(result)

    return random_row

# Function fetching all states matching a given state
def get_state_cluster(current_state):
    # Connect to the database
    db_url = 'sqlite:///slay_the_spire.db'
    db = dataset.connect(db_url)
    table = db['states']

    query = f"""
    SELECT *
    FROM states
    WHERE floor = {current_state['floor']}
    AND ascension_level = {current_state['ascension_level']}
    AND CAST(current_hp as INTEGER)/20 = 1
    AND CAST(max_hp as INTEGER)/20 = 3
    """

    #AND ABS(current_hp - {current_state['current_hp']}) < 10
    #AND ABS(max_hp - {current_state['max_hp']}) < 10

    # AND editdist3(deck, '{json.dumps(current_state['deck'])}') < 30

    # Execute the query
    results = db.query(query)

    return results

def levenshtein_distance(list1, list2):
    len1, len2 = len(list1), len(list2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if list1[i - 1] == list2[j - 1]:
                cost = 0
            else:
                cost = 2 # I want substitution to be 2, not 1
            dp[i][j] = min(dp[i - 1][j] + 1,    # Deletion
                           dp[i][j - 1] + 1,    # Insertion
                           dp[i - 1][j - 1] + cost)  # Substitution

    return dp[len1][len2]

db_url = 'sqlite:///slay_the_spire.db'
db = dataset.connect(db_url)
table = db['states']


'''
# Loop through floors 50 to 0
floor = 48
print(f"Processing floor {floor}...")
victory_rate_list = []
predicted_victory_rate_list = []
victory_rate_error_list = []
custom_threshold = 1.25 + 0.03125*floor
for current_hp_interval in range(8):
    print("Processing current hp interval: ", current_hp_interval)
    for max_hp_interval in range(current_hp_interval, 8):
        print("Processing max hp interval: ", max_hp_interval)
        for i in range(10):
            cluster_states = []
            query = f"""
            SELECT *
            FROM states
            WHERE floor = {floor}
            AND ascension_level = 20
            AND CAST(current_hp as INTEGER)/20 = {current_hp_interval}
            AND CAST(max_hp as INTEGER)/20 = {max_hp_interval}
            ORDER BY RANDOM()
            """
            results = db.query(query)
            print("Initial query done")
            reference_state = None
            reference_deck = None
            reference_relics = None
            for state in results:
                if reference_state is None:
                    reference_state = state
                    reference_deck = sorted(json.loads(state['deck']))
                    reference_relics = sorted(json.loads(state['relics']))
                    continue
                # Now we have a reference state and a state to compare
                deck = sorted(json.loads(state['deck']))
                deck_distance = levenshtein_distance(deck, reference_deck) / len(reference_deck)
                relics = sorted(json.loads(state['relics']))
                relic_distance = levenshtein_distance(relics, reference_relics) / len(reference_relics)
                distance = deck_distance + relic_distance
                if distance < custom_threshold:
                    # Add to cluster_states
                    cluster_states.append(state)
            #print("Distances computed, ", len(cluster_states), " states in cluster")
            # Check if no results
            if reference_state is None:
                break
            if len(cluster_states) > 10:
                # Get win/loss for the reference state
                victory_gt = reference_state['victory']
                # Get average win/loss for the cluster
                victory_rate = sum([state['victory'] for state in cluster_states]) / len(cluster_states)
                print("Cluster size: ", len(cluster_states))
                print("Victory rate: ", victory_rate)
                print("Victory gt: ", victory_gt)
                victory_rate_list.append(victory_rate)
                predicted_victory_rate_list.append(victory_gt)
                victory_rate_error_list.append(abs(victory_rate - victory_gt))
    print("Current statistics")
    print("Victory rate: ", np.mean(victory_rate_list))
    print("Predicted victory rate: ", np.mean(predicted_victory_rate_list))
    print("Error: ", np.mean(victory_rate_error_list))
'''

system_prompt = "You are a superhuman AI evaluating the win probability of a state of a playthrough of Slay the Spire. This state is at floor 49, right before the final boss.  Evaluate the current deck and relics in the context of the current game state (Ascension, Floor, Boss, etc.) along the following dimensions: attack, defense, scaling, synergies, card draw. Predict the probability of winning from this state. Finally, produce a 0/1 prediction of run outcome. To aid your evaluation, you will be provided with up to 5 similar states. Think step by step."

#system_prompt = "You are a superhuman AI evaluating the win probability of a state of a playthrough of Slay the Spire. This state is at floor 49, right before the final boss. Evaluate the current deck and relics in the context of the current game state (Ascension, Floor, Boss, etc.) along the following dimensions: attack, defense, scaling, synergies, card draw. Assess attack and scaling potential against the boss's expected damage patterns. Critically evaluate the deck's defensive capabilities considering Ascension level and the final boss's specific attacks. Ensure the defense setup is reliable and consistent for sustained high-pressure boss phases, especially before important relic/power synergies become fully functional. Significantly weigh the impact of key relic abilities on both offense and defense, ensuring thorough consideration of how synergies translate into practical advantages or disadvantages during critical turns. Evaluate how quickly and effectively key scaling mechanisms like Demon Form come into play and their sustained impact. Emphasize the importance of a reliable defense, particularly given high-damage outputs at high Ascension levels. Consider the effect of current HP in conjunction with relic abilities and potential healing sources under continuous damage scenarios. Account for defensive vulnerabilities, particularly the alignment of defensive cards and the accessibility of critical powers like Barricade. Analyze energy management, including the negative impacts of energy-related relics and the deck's energy costs. Carefully evaluate card play limitations (e.g., due to the Time Eater) and implications of relics that affect healing, like Coffee Dripper. Critically evaluate defensive scaling under high Ascension conditions, particularly under continuous heavy damage. Integrate detailed heuristics from past successful evaluations, particularly emphasizing offensive scaling mechanisms (such as Demon Form and Limit Break) and the consistency of drawing them during prolonged boss fights. Analyze how relic synergies (e.g., Gremlin Horn's interaction with energy and draw management) provide adaptive responses during critical moments. Predict the probability of winning from this state against the specific final boss, considering the unique threats they pose, especially their mechanics (e.g., Time Eater's card limit, Awakened One's scaling, Donu and Deca's dual attacks). Emphasize the importance of evaluating the player's exact HP and the criticality of healing during the final boss fight. Weigh the potential impact of drawing certain cards at specific times (especially during key turns) and the overall consistency of drawing the right combinations to sustain defense or execute attacks. Evaluate the impacts of curses/status cards on the deck's real potential during the final encounter. Think step by step. Ensure an equally weighted consideration of offensive and defensive potential, including the integration of countermeasures against continuous high-damage outputs from bosses. Specifically address the significance of managing trash cards like AscendersBane and assess both immediate and sustained survival tactics. Evaluate defensive and offensive turn-by-turn play, considering the impact of the Time Eater's card-play-limiting effect and ensuring that critical cards are prioritized. Remove references to irrelevant relics like Ectoplasm, streamline evaluation for existing ones. Focus on evaluating different defensive tactics in response to the specific attack patterns of each final boss. Identify 'must draw' cards crucial for key turns, focusing not only on drawing but also on draw consistency, and impact of energy management and available energy in sustaining card play. Produce a 0/1 prediction of the run outcome. Use detailed analysis from similar past predictions and feedback to inform your conclusion. Sharpen the focus on the consistency of draw and potential relic-induced inconsistencies, such as the effects of Snecko Eye."

nn_mode = False
need_similar_states = False
if nn_mode:
    need_similar_states = True
# Generate random hex run id
run_id = random.randint(0, 1000000)
losses = []
preds = []
gts = []
for i in range(20):
    query = f"""
    SELECT *
    FROM states
    WHERE floor = 49
    AND ascension_level = 20
    ORDER BY RANDOM()
    """
    results = db.query(query)
    print("Initial query done")

    reference_state = None
    reference_deck = None
    reference_relics = None
    states = []
    dists = []
    for state in results:
        del state['potions']
        del state['actions_taken']
        del state['deck']
        if reference_state is None:
            reference_state = state
            reference_deck = sorted(json.loads(state['master_deck']))
            reference_relics = sorted(json.loads(state['relics']))
            continue
        # Now we have a reference state and a state to compare
        deck = sorted(json.loads(state['master_deck']))
        deck_distance = levenshtein_distance(deck, reference_deck) / len(reference_deck)
        relics = sorted(json.loads(state['relics']))
        relic_distance = levenshtein_distance(relics, reference_relics) / len(reference_relics)
        distance = deck_distance + relic_distance
        #hp_percent_diff = np.abs(state['current_hp'] - reference_state['current_hp']) / reference_state['current_hp']
        #distance += hp_percent_diff * 0.5
        if distance < 2.25:
            # Add to cluster_states
            dists.append(distance)
            states.append(state)
        if len(states) >= 200:
            break
    
    #sort states by dists
    # Get ordering across dists
    sorted_idxs = np.argsort(dists)
    # Apply ordering to states
    if need_similar_states:
        similar_states = [states[i] for i in sorted_idxs][:5]
    else:
        similar_states = None
    #similar_states = [x for _, x in sorted(zip(dists, states))][:5]

    if nn_mode:
        # Get average victory rate in 5 states
        print("Using NN")
        print("Similar states: ", len(similar_states))
        if len(similar_states) == 0:
            avg_victory_rate = 0.5
        else:
            avg_victory_rate = sum([state['victory'] for state in similar_states]) / len(similar_states)
            if avg_victory_rate < 0.5:
                avg_victory_rate = 0
            else:
                avg_victory_rate = 1
        gt_win = reference_state['victory']

        loss = np.abs(avg_victory_rate - gt_win)
        losses.append(loss)
        preds.append(avg_victory_rate)
        gts.append(gt_win)
        continue

    print("Using LLM")

    gt_win = reference_state['victory']
    gt_score = reference_state['score']

    print("win? ", gt_win)

    del reference_state['victory']
    del reference_state['score']

    print("Reference state: ", reference_state)
    
    system_prompt, llm_pred = win_prediction(system_prompt, reference_state, similar_states, run_id)

    print("Prediction: ", llm_pred)

    try:
        try:
            llm_pred = ast.literal_eval(llm_pred)
        except:
            try:
                llm_pred = json.loads(llm_pred)
            except:
                try:
                    llm_pred = json.loads(llm_pred.replace("'", "\""))
                except:
                    llm_pred = eval(llm_pred)
        pred_victory = (int)(llm_pred['predicted_outcome'])
        losses.append(np.abs(pred_victory - gt_win))
        preds.append(pred_victory)
        gts.append(gt_win)
    except Exception as e:
        print("Error: ", e)

    # Now see how we'd modify the system prompt

    x = update_win_prediction_prompt(system_prompt, reference_state, similar_states, str(llm_pred), "The run actually resulted in a " + ("win" if gt_win == 1 else "loss"), run_id)

    print("Updated prompt: ", x)

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

print("Losses: ", losses)
print("Mean loss: ", np.mean(losses))
print("Max loss: ", np.max(losses))
print("Min loss: ", np.min(losses))
print("Preds: ", preds)
print("Gts: ", gts)




