import dataset
import json

def export_db_to_json(db_url, output_json_file):
    db = dataset.connect(db_url)
    table = db['states']
    
    # Fetch all records from the table
    records = table.all()
    
    # Convert records to a list of dictionaries
    data = [dict(record) for record in records]
    
    # Write the data to a JSON file
    with open(output_json_file, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Example usage
db_url = 'sqlite:///slay_the_spire.db'
output_json_file = 'slay_the_spire_export.json'
export_db_to_json(db_url, output_json_file)
