import dataset
import pandas
import numpy as np

# Get min floor where cluster_id field is populated
def get_min_floor():
    db = dataset.connect('sqlite:///slay_the_spire.db')
    query = """
        SELECT *
        FROM states
        WHERE cluster_id == 246
    """
    result = db.query(query)
    return result

# Compute average victory rate in x
# Use numpy to compute the average
def compute_victory_rate(x):
    return np.mean(x['victory'])

# Get how many A20 states there are
def get_a20_states():
    db = dataset.connect('sqlite:///slay_the_spire.db')
    query = """
        SELECT *
        FROM states
        WHERE ascension_level == 20
        AND floor > 31
        AND cluster_id IS NOT NULL
    """
    result = db.query(query)
    return result

'''
x = get_min_floor()

print(compute_victory_rate(x))
'''

x = get_a20_states()

# Convert to pandas
df = pandas.DataFrame(x)

def compute_value(df, cluster_states):
    values = []
    #print("Cluster states", cluster_states)
    # Loop over all states in the cluster
    for index, x in cluster_states.iterrows():
        #print("Entry", x)
        # Get the run id
        run_id = x['play_id']
        # Get the victory rate for the next floor
        next_floor = x['floor'] + 1
        # Get all states for the next floor where id is the same as the current run id
        next_states = df[(df['floor'] == next_floor) & (df['play_id'] == run_id)]
        # Check if there are any states for the next floor
        if len(next_states) == 0:
            # Then we set value to 0
            values.append(0)
        else:
            # Filter out nans from next_states['value']
            next_states = next_states.dropna(subset=['value'])
            # If empty, continue
            if len(next_states) == 0:
                values.append(0)
            # Otherwise we compute the victory rate
            values.append(next_states['value'].mean())
    #if len(cluster_states) > 30:
    #    print("Values", values)
    if np.isnan(np.mean(values)):
        print("Values", values)
        print("Cluster states", cluster_states)
        exit()
    return np.mean(values)

# Now we need to basically compute the value for every cluster, working back from floor 48

for floor in range(48, 0, -1):
    print(f"Computing victory rate for floor {floor}")
    # Get all states for this floor
    states = df[df['floor'] == floor]
    
    # Get all unique cluster ids
    cluster_ids = states['cluster_id'].unique()
    # Remove nan from this
    cluster_ids = cluster_ids[~np.isnan(cluster_ids)]

    # Loop through all cluster ids
    for cluster_id in cluster_ids:
        # Get all states for this cluster
        cluster_states = states[states['cluster_id'] == cluster_id]

        if len(cluster_states) == 0:
            print("Huh? Empty cluster", cluster_id)
            exit()

        # Continue if cluster has less than 30 states
        #if len(cluster_states) < 30:
        #    continue

        # Compute average victory rate
        if floor == 48:
            value = compute_victory_rate(cluster_states)
        else:
            value = compute_value(df, cluster_states)
            monte_carlo_value = compute_victory_rate(cluster_states)
            if len(cluster_states) > 30:
                print("Monte Carlo error", abs(value - monte_carlo_value))
                print("Monte Carlo value", monte_carlo_value)

        if len(cluster_states) > 30:
            print(f"Cluster {cluster_id} has value {value}")

        # Update the cluster with this victory rate
        df.loc[df['cluster_id'] == cluster_id, 'value'] = value