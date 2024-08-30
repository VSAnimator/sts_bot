from flask import Flask, request, jsonify, render_template
import dataset
import datetime
from os import listdir
from os.path import isfile, join

app = Flask(__name__)
db = dataset.connect('sqlite:///labeling.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_states', methods=['GET'])
def get_states():
    timestamp = request.args.get('timestamp')
    states = list(db['states'].find(timestamp=timestamp))
    if states:
        return jsonify(states)
    else:
        return jsonify({"error": "States not found"}), 404

@app.route('/search_states', methods=['GET'])
def search_states():
    query = request.args
    print(query)
    conditions = []
    key = query.get('key')
    value = query.get('value')
    comparison = query.get('comparison')
    if comparison in ['>', '<', '=']:  # integer fields
        conditions.append(f"{key} {comparison} {int(value)}")
    else:  # string fields
        conditions.append(f"{key} LIKE '%{value}%'")
    
    sql_query = f"SELECT * FROM states WHERE {' AND '.join(conditions)}"
    print("Query, ", sql_query)
    result = db.query(sql_query)
    states = list(result)
    if states:
        return jsonify(states)
    else:
        return jsonify({"error": "No matching states found"}), 404

@app.route('/get_keys', methods=['GET'])
def get_keys():
    # Assuming the table 'states' exists and we want to get the column names
    result = db.query("PRAGMA table_info(states)")
    keys = [row['name'] for row in result]
    return jsonify(keys)

def log_labeled_state(updated_state):
    """Logs the labeled state to a text file."""
    log_entry = f"{datetime.datetime.now()}: {updated_state}\n"
    with open('labeled_states.log', 'a') as log_file:
        log_file.write(log_entry)

@app.route('/label_choice', methods=['POST'])
def label_choice():
    data = request.json

    id = data.get('id')
    choice = data.get('choice')
    print(id, choice)

    try:
        # Access the 'states' table
        table = db['states']
        
        # Update the record where 'game_state_seed' and 'step' match
        #result = table.update({'game_state_seed': int(gameStateSeed), 'step': int(step), 'label': choice}, ['game_state_seed', 'step'])
        result = table.update({'id': id, 'label': choice}, ['id'])

        print("Database result", result)
        # Show updated record
        log_labeled_state(table.find_one(id=int(id)))

        # Check if the update was successful
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No record found to update'})
        
    except Exception as e:
        # Handle any errors and return a failure response
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_filenames', methods=['GET'])
def get_filenames():
    # Get the unique values from the 'timestamp' column in the 'states' table
    filenames = db.query('SELECT DISTINCT timestamp FROM states')
    return jsonify([f['timestamp'] for f in filenames])
    '''
    # Assuming the folder path is 'timestamps_folder'
    folder_path = 'valid_folders_archive'
    try:
        # Get list of filenames in the folder
        onlyfiles = [f for f in listdir(folder_path) if not isfile(join(folder_path, f))]
        # Optionally, filter or sort the filenames as needed
        return jsonify(onlyfiles)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    '''

if __name__ == '__main__':
    app.run(debug=True)
