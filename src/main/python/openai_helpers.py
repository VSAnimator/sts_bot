from openai import OpenAI
import json

client = OpenAI()

# Read the system prompt from the file system.txt
with open('prompts/system.txt', 'r') as file:
    system_prompt = file.read()

def get_text(prompt):
    try:
        prompt = json.dumps(prompt)
        print("Prompt type: ", type(prompt))
        print("System type: ", type(system_prompt))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
            #top_p=1
        )
        return response
    except Exception as e:
        print("Exception: ", e)
        raise Exception("Failed to get text.")