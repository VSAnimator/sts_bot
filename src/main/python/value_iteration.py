import dataset
import json
from collections import Counter
import numpy as np
import random

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

'''
# Calculate similarity between two states

x = query_random_state()
print(x)

similar = get_state_cluster(x)

reference_deck = sorted(json.loads(x['deck']))
reference_relics = sorted(json.loads(x['relics']))
reference_floor = x['floor']

decks = []
all_relics = []
victories = []
dists = []
for elem in similar:
    print(elem)
    deck = sorted(json.loads(elem['deck']))
    print("Deck: ", deck)
    print("Reference deck: ", reference_deck)
    distance = levenshtein_distance(deck, reference_deck) / len(reference_deck)
    # Add on relics
    relics = sorted(json.loads(elem['relics']))
    print("Relics: ", relics)
    print("Reference relics: ", reference_relics)
    distance += levenshtein_distance(relics, reference_relics) / len(reference_relics)
    print("Distance: ", distance)
    print("\n")
    decks.append(deck)
    dists.append(distance)
    all_relics.append(relics)
    victories.append(elem['victory'])

# Get the top 5 matching decks and their distances
top_decks = [deck for _, deck in sorted(zip(dists, decks))][:5]
top_distances = sorted(dists)[:5]

print("Reference deck: ", reference_deck)
print("Top decks: ", top_decks)
print("Top distances: ", top_distances)

# Same for relics
top_relics = [relics for _, relics in sorted(zip(dists, all_relics))][:5]
top_distances = sorted(dists)[:5]

print("Reference relics: ", reference_relics)
print("Top relics: ", top_relics)
print("Top distances: ", top_distances)

custom_threshold = 1.25 + 0.03125*reference_floor

for threshold in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, custom_threshold]:
    dist_count = sum(1 for dist in dists if dist < threshold)
    print(f"Number of distances less than {threshold}: {dist_count}")
    if dist_count == 0:
        continue
    victory_rate = sum(1 for i, dist in enumerate(dists) if dist < threshold and victories[i]) / dist_count
    print(f"Fraction of victories at distance less than {threshold}: {victory_rate}")

# Add a cluster_id column to the database where the cluster_id is the id of the reference state, and populate with cluster_id for all elements below the custom threshold distance
# Make a new table with the cluster_id as the primary key and the reference state as a foreign key
# Add a new column to the states table with the cluster_id as a foreign key

'''

db_url = 'sqlite:///slay_the_spire.db'
db = dataset.connect(db_url)
table = db['states']

if not db['value_table'].exists:
    # Define the table
    value_table = db.create_table('value_table', primary_id='cluster_id', primary_type=db.types.integer)
    # Add an additional column with float type
    value_table.create_column('value', db.types.float)
else:
    value_table = db['value_table']

# Q-table
if not db['q_table'].exists:
    q_table = db.create_table('q_table', primary_id='cluster_id', primary_type=db.types.integer)
    q_table.create_column('action', db.types.text)
    q_table.create_column('value', db.types.float)
else:
    q_table = db['q_table']

# Have an in-memory dictionary to store the values as well
value_dict = {}

# Create indexes
print("Creating indices for faster queries...")
db.query("CREATE INDEX IF NOT EXISTS idx_states_play_id ON states(play_id)")
print("One index created")
db.query("CREATE INDEX IF NOT EXISTS idx_states_floor ON states(floor)")
print("Two indices created")
db.query("CREATE INDEX IF NOT EXISTS idx_states_ascension_level ON states(ascension_level)")
print("Three indices created")
db.query("CREATE INDEX IF NOT EXISTS idx_states_current_hp ON states(CAST(current_hp as INTEGER)/20)")
print("Four indices created")
db.query("CREATE INDEX IF NOT EXISTS idx_states_max_hp ON states(CAST(max_hp as INTEGER)/20)")
print("Five indices created")

# Loop through floors 50 to 0
for floor in range(43, -1, -1):
    print(f"Processing floor {floor}...")
    custom_threshold = 1.25 + 0.03125*floor
    for current_hp_interval in range(8):
        print("Processing current hp interval: ", current_hp_interval)
        for max_hp_interval in range(current_hp_interval, 8):
            print("Processing max hp interval: ", max_hp_interval)
            while True:
                query = f"""
                SELECT *
                FROM states
                WHERE floor = {floor}
                AND ascension_level = 20
                AND CAST(current_hp as INTEGER)/20 = {current_hp_interval}
                AND CAST(max_hp as INTEGER)/20 = {max_hp_interval}
                AND cluster_id IS NULL
                """
                results = db.query(query)
                print("Initial query done")
                reference_state = None
                reference_deck = None
                reference_relics = None
                cluster_states = []
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
                        # Add cluster_id to the state
                        table.update({'id': state['id'],'cluster_id': reference_state['id']}, ['id'])
                print("Distances computed, ", len(cluster_states), " states in cluster")
                # Check if no results
                if reference_state is None:
                    break
                else:
                    table.update({'id': reference_state['id'],'cluster_id': reference_state['id']}, ['id'])
                cluster_states.append(reference_state)
            '''
            # Now we compute the value and q-values for the cluster
            q_values = {}
            values = []
            for state in cluster_states:
                # If level 50 get win/loss as value, otherwise get the value from the next level
                if state['floor'] == 49:
                    value = 1 if state['victory'] else 0
                else:
                    next_floor = state['floor'] + 1
                    next_query = f"""
                    SELECT cluster_id
                    FROM states
                    WHERE play_id = '{state['play_id']}'
                    AND floor = {next_floor}
                    """
                    # Run the query, if no results set value to 0
                    next_results = db.query(next_query)
                    next_state = next_results.next()
                    print("Next state: ", next_state)
                    if next_state['cluster_id'] is None:
                        value = 0
                    else:
                        # Query the value table for the value of the next state
                        value_query = f"""
                        SELECT value
                        FROM value_table
                        WHERE cluster_id = {next_state['cluster_id']}
                        """
                        # Get value from query
                        value_results = db.query(value_query)
                        value = value_results.next()['value'] if value_results else 0
                        #value_dict[next_state['cluster_id']]
                values.append(value)
                # Now extract the actions taken
                actions_taken = json.loads(state['actions_taken'])
                state_actions = [action for action in actions_taken if 'Card picked' in action]
                for action in actions_taken:
                    if action.find("Event") >= 0:
                        continue # Maybe add this later...
                    elif action.find("Potion") >= 0:
                        continue # Potion tracking is broken
                    else:
                        action = action.split(", ")[0]
                        if action not in q_values:
                            q_values[action] = [value]
                        else:
                            q_values[action].append(value)
            # Now compute overall values and qs for the cluster
            overall_value = np.mean(values)
            for action in q_values:
                q_values[action] = np.mean(q_values[action])
            # Add to tables and dict
            cluster_id = reference_state['id']
            value_table.upsert({'cluster_id': cluster_id, 'value': overall_value}, ['cluster_id'])
            value_dict[cluster_id] = overall_value
            for action in q_values:
                q_table.upsert({'cluster_id': cluster_id, 'action': action, 'value': q_values[action]}, ['cluster_id', 'action'])
            print("Value dict", value_dict)
            '''