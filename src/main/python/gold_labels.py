import dataset

# Connect to Joe's, Pasha's, and Policy databases
joe_db_url = 'sqlite:///labeling_joe.db'
pasha_db_url = 'sqlite:///labeling_pasha.db'
policy_db_url = 'sqlite:///policy.db'

joe_db = dataset.connect(joe_db_url)
pasha_db = dataset.connect(pasha_db_url)
policy_db = dataset.connect(policy_db_url)

def get_conflicting_labels():
    # Access the 'states' table in both databases
    joe_table = joe_db['states']
    pasha_table = pasha_db['states']

    # Fetch labeled rows from both Joe's and Pasha's tables
    joe_labeled_rows = {row['id']: row['label'] for row in joe_table.find(label={'not': None})}
    pasha_labeled_rows = {row['id']: row['label'] for row in pasha_table.find(label={'not': None})}

    # Find rows labeled by both Joe and Pasha with conflicting labels
    conflicting_rows = []
    for id, joe_label in joe_labeled_rows.items():
        if id in pasha_labeled_rows:
            pasha_label = pasha_labeled_rows[id]
            if joe_label != pasha_label:
                # Fetch the full row data (can adjust what to display as needed)
                joe_row = joe_table.find_one(id=id)
                pasha_row = pasha_table.find_one(id=id)
                conflicting_rows.append({
                    'id': id,
                    'joe_label': joe_label,
                    'pasha_label': pasha_label,
                    'joe_row': joe_row,
                    'pasha_row': pasha_row
                })

    # Display or return the conflicting rows
    for conflict in conflicting_rows:
        print(f"Conflict found for id {conflict['id']}:")
        # Print the floor
        print("Floor: ", conflict['joe_row']['game_state_floor'])
        print(f"  Joe's label: {conflict['joe_label']}")
        print(f"  Pasha's label: {conflict['pasha_label']}")
        #print(f"  Joe's row: {conflict['joe_row']}")
        #print(f"  Pasha's row: {conflict['pasha_row']}")
        print()

    print(f"Total conflicting rows: {len(conflicting_rows)}")
    # Also print total rows from each
    print(f"Total Joe labeled rows: {len(joe_labeled_rows)}")
    print(f"Total Pasha labeled rows: {len(pasha_labeled_rows)}")

    return conflicting_rows


def get_agreements_and_check_with_bot_response():
    # Access the 'states' table in both databases
    joe_table = joe_db['states']
    pasha_table = pasha_db['states']

    # Fetch labeled rows from both Joe's and Pasha's tables
    joe_labeled_rows = {row['id']: row['label'] for row in joe_table.find(label={'not': None})}
    pasha_labeled_rows = {row['id']: row['label'] for row in pasha_table.find(label={'not': None})}

    # Find rows labeled by both Joe and Pasha with the same label
    agreement_rows = []
    disagreement_rows = []
    correct_bot_response_rows = []

    for id, joe_label in joe_labeled_rows.items():
        if id in pasha_labeled_rows:
            pasha_label = pasha_labeled_rows[id]
            if joe_label == pasha_label:
                # Fetch the full row data for comparison with bot_response
                joe_row = joe_table.find_one(id=id)
                pasha_row = pasha_table.find_one(id=id)

                # Check if agreed label matches the bot_response field
                bot_response = joe_row.get('bot_response')  # Assuming bot_response is the same in both rows
                if bot_response is not None:
                    if joe_label != bot_response:
                        agreement_rows.append({
                            'id': id,
                            'label': joe_label,
                            'bot_response': bot_response,
                            'joe_row': joe_row,
                            'pasha_row': pasha_row
                        })
                    else:
                        correct_bot_response_rows.append({
                            'id': id,
                            'label': joe_label,
                            'bot_response': bot_response,
                            'joe_row': joe_row,
                            'pasha_row': pasha_row
                        })
            else:
                # Track disagreements for potential further analysis
                disagreement_rows.append({
                    'id': id,
                    'joe_label': joe_label,
                    'pasha_label': pasha_label
                })

    # Display or return rows where agreement does not match bot_response
    print("Agreed rows where label does not match bot_response:")
    for row in agreement_rows:
        print(f"ID: {row['id']}, Label: {row['label']}, Bot Response: {row['bot_response']}")
        print("Choice list: ", row['joe_row']['game_state_choice_list'])
        #print(f"Joe's Row: {row['joe_row']}")
        #print(f"Pasha's Row: {row['pasha_row']}")
        print()

    print("Consensus rows:")
    for row in correct_bot_response_rows:
        print(f"ID: {row['id']}, Label: {row['label']}, Bot Response: {row['bot_response']}")
        print("Choice list: ", row['joe_row']['game_state_choice_list'])
        #print(f"Joe's Row: {row['joe_row']}")
        #print(f"Pasha's Row: {row['pasha_row']}")
        print()

    print(f"States where Pasha and Joe disagree: {len(disagreement_rows)}")
    print(f"States where Pasha and Joe agree: {len(agreement_rows) + len(correct_bot_response_rows)}")
    print(f"Total correct bot response rows: {len(correct_bot_response_rows)}")
    print(f"Total incorrect bot response rows: {len(agreement_rows)}")

    return agreement_rows, disagreement_rows

def evaluate_policy_agreements():
    # Access the 'states' table in Joe's and Pasha's databases, and the 'policy' table in Policy database
    joe_table = joe_db['states']
    pasha_table = pasha_db['states']
    policy_table = policy_db['states']

    # Fetch labeled rows from Joe's and Pasha's tables
    joe_labeled_rows = {row['id']: row for row in joe_table.find(label={'not': None})}
    pasha_labeled_rows = {row['id']: row for row in pasha_table.find(label={'not': None})}

    # Prepare lists for rows where Joe and Pasha agreed and disagreed
    agreement_rows = []
    disagreement_rows = []

    floor = -1
    # Check rows where Joe and Pasha labeled the same id
    for id, joe_row in joe_labeled_rows.items():
        if id in pasha_labeled_rows:
            pasha_row = pasha_labeled_rows[id]
            if joe_row['label'] == pasha_row['label']:
                # Continue if floor is same as current floor
                if joe_row['game_state_floor'] == floor:
                    continue
                floor = joe_row['game_state_floor']
                # Fetch the policy row matching on timestamp and step
                timestamp = joe_row['timestamp']
                step = joe_row['step']
                policy_row = policy_table.find_one(timestamp=timestamp, step=step)
                
                if policy_row:
                    policy_response = policy_row['policy_response']
                    agreed_label = joe_row['label']

                    # Check agreement and disagreement between policy and human label
                    if agreed_label == policy_response:
                        agreement_rows.append({
                            'id': id,
                            'timestamp': timestamp,
                            'step': step,
                            'label': agreed_label,
                            'policy_response': policy_response,
                            'joe_row': joe_row,
                            'pasha_row': pasha_row,
                            'policy_row': policy_row
                        })
                    else:
                        disagreement_rows.append({
                            'id': id,
                            'timestamp': timestamp,
                            'step': step,
                            'label': agreed_label,
                            'policy_response': policy_response,
                            'joe_row': joe_row,
                            'pasha_row': pasha_row,
                            'policy_row': policy_row
                        })

    # Display results
    print("Agreements between policy and Joe/Pasha:")
    for row in agreement_rows:
        print("Floor: ", row['joe_row']['game_state_floor'])
        print(f"ID: {row['id']}, Timestamp: {row['timestamp']}, Step: {row['step']}")
        print(f"  Joe and Pasha Label: {row['label']}")
        print(f"  Policy Response: {row['policy_response']}")
        print()

    print("Disagreements between policy and Joe/Pasha:")
    for row in disagreement_rows:
        # Print floor
        print("Floor: ", row['joe_row']['game_state_floor'])
        print(f"ID: {row['id']}, Timestamp: {row['timestamp']}, Step: {row['step']}")
        print(f"  Joe and Pasha Label: {row['label']}")
        print(f"  Policy Response: {row['policy_response']}")
        print()

    print(f"Total agreements: {len(agreement_rows)}")
    print(f"Total disagreements: {len(disagreement_rows)}")

    return agreement_rows, disagreement_rows

# Run the function to find and display conflicts
if __name__ == '__main__':
    #get_conflicting_labels()
    #get_agreements_and_check_with_bot_response()
    #evaluate_policy_agreements()

    joe_table = joe_db['states']

    # Fetch labeled rows from both Joe's and Pasha's tables
    joe_labeled_rows = {row['id']: row['label'] for row in joe_table.find(label={'not': None})}

    # Print the first joe row for each floor
    floor_dict = {}
    for id, label in joe_labeled_rows.items():
        row = joe_table.find_one(id=id)
        floor = row['game_state_floor']
        # Skip the ones with stolen_gold, emerald_key, or open
        if "stolen_gold" in row['game_state_choice_list'] or "emerald_key" in row['game_state_choice_list'] or "open" in row['game_state_choice_list']:
            continue
        if floor not in floor_dict:
            floor_dict[floor] = row
    
    for floor, row in floor_dict.items():
        print("Floor: ", floor)
        print("ID: ", row['id'])
        print("Timestamp: ", row['timestamp'])
        print("Label: ", row['label'])
        print("Bot Response: ", row['bot_response'])
        print("Choice List: ", row['game_state_choice_list'])
        print()
