from openai import OpenAI

filename = "1718348700.830403"

client = OpenAI()

with open("runs/" + filename + ".txt", "r") as file:
    trajectory_file = file.read()
# Split into a list line by line
trajectory = trajectory_file.split("\n")

final_state = trajectory[-2]

with open('prompts/system_analysis.txt', 'r') as file:
    system_prompt = file.read()
system_prompt = system_prompt.replace('INSERT', final_state)

print("System prompt: ", system_prompt)

# Make a file to write to
write_file = open("runs_processed/" + filename + ".txt", "w")

# Create tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "store_state_action_rating",
            "description": "Store rating of bot action at a given state",
            "parameters": {
                "type": "object",
                "properties": {
                    "rating": {
                        "type": "string",
                        "description": "Rating the bot action (-1 for bad, 1 for good, 0 for neutral)",
                        "enum": ["-1", "0", "1"]
                    },
                    "best_action": {"type": "string"},
                },
                "required": ["rating", "best_action"],
            },
        },
    }
]

# Now loop through the trajectory and analyze each decision
for i in range(len(trajectory) - 1):
    try:
        state = trajectory[i]
        # Check if its a bot action
        if "Bot response: " not in state:
            continue
        # Now put together prompt as last two elements of trajectory
        prompt = "Evaluate this decision by the metagame bot: " + trajectory[i - 1] + "\n" + trajectory[i]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            tools=tools,
            tool_choice="required"
        )
        print("Response: ", response.choices[0].message.tool_calls[0].function.arguments)
        split_response = str(response.choices[0].message.tool_calls[0].function.arguments)
        write_file.write(split_response + "\n")
    except Exception as e:
        print("Exception: ", e)
        write_file.write("Failed to get text.\n")
