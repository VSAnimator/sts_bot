import dataset
import ast
from openai import OpenAI
import json
import os
import numpy as np

db = dataset.connect('sqlite:///act1.db')

# Create tables for runs and for individual states
run_table = db['runs']
state_table = db['states']

# Filter by Neow event, group by response, return win pct
query = '''
select avg(victory)
from runs, states
where runs.id == states.run_id
and event_name == 'Neow Event'
group by bot_response
'''

query = '''
select bot_response, avg(victory), count(*)
from runs, states
where runs.id == states.run_id
and event_name == "Neow"
group by bot_response
'''

print(state_table.columns)
print(run_table.columns)

results = db.query(query)

for result in results:
    print(result)