from flask import Flask, request, jsonify, render_template
import dataset

app = Flask(__name__)
db = dataset.connect('sqlite:///mydatabase.db')

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

if __name__ == '__main__':
    app.run(debug=True)
