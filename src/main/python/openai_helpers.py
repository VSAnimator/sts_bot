from openai import OpenAI
import json

client = OpenAI()

# Read the system prompt from the file system.txt
with open('prompts/system.txt', 'r') as file:
    system_prompt = file.read()

# Load v2 system prompt
with open('prompts/system_v2.txt', 'r') as file:
    system_prompt_v2 = file.read()

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

def get_text_v2(prompt):
    try:
        # Get the valid options out of the prompt
        all_options = prompt['available_commands']
        # If "choose" is one of the options, then "roll" the other options into the choice list
        if "choose" in all_options:
            all_options = [command for command in all_options if command != "choose"]
            # For all commands in choice_list, append the word "choose " to the front
            for i in range(len(prompt['game_state']['choice_list'])):
                prompt['game_state']['choice_list'][i] = "choose " + prompt['game_state']['choice_list'][i]
            all_options.extend(prompt['game_state']['choice_list'])
        # Great, now these can be passed as options to the GPT tool call
        # Delete them from the state
        del prompt['available_commands']
        del prompt['game_state']['choice_list']
            
        # Augment system prompt with task-specific information
        act_id = prompt['game_state']['act']
        screen_type = prompt['game_state']['screen_type']
        if screen_type == "CARD_REWARD":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_cards.txt"
        elif screen_type == "SHOP_SCREEN":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_merchant.txt"
        elif screen_type == "MAP":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_pathing.txt"
        elif screen_type == "GRID":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_upgrades.txt"
        else:
            custom_file_name = None
        if custom_file_name:
            with open(custom_file_name, 'r') as file:
                custom_prompt = file.read()
            system_prompt_custom = system_prompt_v2.replace('INSERT', custom_prompt)
        else:
            system_prompt_custom = system_prompt_v2.replace('INSERT', "")

        prompt = json.dumps(prompt)

        # Define the tool: return both the chosen action from the enum and a short explanation
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "choose_best_action",
                    "description": "Choose the best action to take from a list of options, given the current state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chosen_action": {
                                "type": "string",
                                "description": "the action that will be taken by the metagame AI",
                                "enum": all_options
                            },
                            "explanation": {
                                "type": "string",
                                "description": "A short (1-sentence) explanation of why the action was chosen"
                                },
                        },
                        "required": ["chosen_action", "explanation"],
                    },
                },
            }
        ]

        print("System prompt: ", system_prompt_custom)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": [{"type": "text", "text": system_prompt_custom}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            tools=tools,
            tool_choice="required"
        )
        return response
    except Exception as e:
        print("Exception: ", e)
        raise Exception("Failed to get text.")