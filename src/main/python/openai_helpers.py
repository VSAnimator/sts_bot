from openai import OpenAI
import json
import numpy as np
import ast
import os

# Read the system prompt from the file system.txt
with open('prompts/system.txt', 'r') as file:
    system_prompt = file.read()

# Load v2 system prompt
with open('prompts/system_v2.txt', 'r') as file:
    system_prompt_v2 = file.read()

# Load v3 system prompt
with open('prompts/system_v3.txt', 'r') as file:
    system_prompt_v3 = file.read()

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

def get_text_v2(prompt, session_id):
    # Set up the client with helicone logging
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"{session_id}"
        }
    )

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
            if prompt['game_state']['screen_state']['for_upgrade'] == True:
                custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_upgrades.txt"
            else:
                custom_file_name = None
        elif screen_type == "EVENT" and prompt['game_state']['screen_state']['event_id'] == "Neow Event":
            custom_file_name = "prompts/sub_prompts/neow.txt"
        else:
            custom_file_name = None
        if custom_file_name:
            with open(custom_file_name, 'r') as file:
                custom_prompt = file.read()
            if screen_type == "MAP":
                custom_prompt = custom_prompt + "\n" + "For each pathing option, 'expanded_next_nodes' contains a condensed representation of all the nodes you will have to visit before the next pathing decision. Use this to help decide which path to take." 
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

        # Temporary test
        #system_prompt_custom = system_prompt

        for i in range(3):
            if i > 0:
                print("Retrying...")
            gpt_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": system_prompt_custom}]},
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                tools=tools,
                tool_choice="required"
            )
            print("Gpt response: ", gpt_response)
            # Check that it's valid
            response = gpt_response.choices[0].message.tool_calls[0].function.arguments
            response = ast.literal_eval(response)
            response = response['chosen_action']
            if response in all_options:
                return response
        # Set the response to something random from the available commands
        return np.random.choice(all_options)
    except Exception as e:
        print("Exception: ", e)
        print("Sad")
        raise Exception("Failed to get text.")

def get_text_v3(prompt, session_id, similar_states):
    # Set up the client with helicone logging
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"{session_id}"
        }
    )

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
        # For sozu, we need to remove options containing "potion" from the list of options when in the shop
        if "sozu" in prompt['game_state']['relics'] and prompt['game_state']['screen_type'] == "SHOP_SCREEN":
            all_options = [command for command in all_options if "potion" not in command]

        # Great, now these can be passed as options to the GPT tool call
        # Delete them from the state
        del prompt['available_commands']
        del prompt['game_state']['choice_list']
        #prompt['command_options'] = all_options # Pass it in for the first LLM call
            
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
            if prompt['game_state']['screen_state']['for_upgrade'] == True:
                custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_upgrades.txt"
            else:
                custom_file_name = None
        elif screen_type == "EVENT" and prompt['game_state']['screen_state']['event_id'] == "Neow Event":
            custom_file_name = "prompts/sub_prompts/neow.txt"
        else:
            custom_file_name = None
        if custom_file_name:
            with open(custom_file_name, 'r') as file:
                custom_prompt = file.read()
            if screen_type == "MAP":
                custom_prompt = custom_prompt + "\n" + "For each pathing option, 'expanded_next_nodes' contains a condensed representation of all the nodes you will have to visit before the next pathing decision. Use this to help decide which path to take." 
            system_prompt_custom = system_prompt_v3.replace('INSERT', "Advice from Joe, an expert player: " + custom_prompt)
        else:
            system_prompt_custom = system_prompt_v3.replace('INSERT', "")

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
                            "explanation": {
                                "type": "string",
                                "description": "A short (1-sentence) explanation of why the action was chosen"
                            },
                            "chosen_action": {
                                "type": "string",
                                "description": "the action that will be taken by the metagame AI",
                                "enum": all_options
                            },
                        },
                        "required": ["explanation", "chosen_action"],
                    },
                },
            }
        ]

        print("System prompt: ", system_prompt_custom)

        # Temporary test
        #system_prompt_custom = system_prompt

        for i in range(3):
            if i > 0:
                print("Retrying...")
            prompt = prompt + "\n" + "1. Evaluate the current deck and relics in the context of the current game state (Ascension, Level, Boss, etc.) along the following four dimensions: attack, defense, scaling, synergies. Return a 1-2 sentence evaluation for each dimension."
            current_messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt_custom}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
            gpt_response = client.chat.completions.create(
                model="gpt-4o",
                messages=current_messages,
            )
            # Add the response to the current_messages
            current_messages.append({"role": "system", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})
            # Evaluate each of the current options
            prompt = "Now, evaluate each of the choices available in context of the current deck and relics, considering how each choice contributes to both the short-term (defeating coming enemies) and the long-term (defeating the Act boss). Return a 1-2 sentence evaluation for each choice." + "\n" + "Choices available: " + str(all_options)

            current_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
            # Again call GPT
            gpt_response = client.chat.completions.create(
                model="gpt-4o",
                messages=current_messages,
            )
            current_messages.append({"role": "system", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})

            if similar_states:
                # Stick the top 3 similar states in the prompt
                prompt = "To help your decision, here are the top 5 most similar states from a database of human playthroughs, where the 'actions taken' field annotates the choices the human made at a particular state: " + str(similar_states[:5])
                prompt += "\n" + "Analyze these states and compare them to the current state. What can be learned from the decisions humans made in these states? Strongly consider making choices similar to human choices from the 'actions taken' field."
                current_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                gpt_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=current_messages,
                )
                current_messages.append({"role": "system", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})

            # Chose one of the options
            prompt = "Given this evaluation, which of the choices is the best choice to take to maximize the chances of winning the run?"
            current_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
            gpt_response = client.chat.completions.create(
                model="gpt-4o",
                messages=current_messages,
                tools=tools,
                tool_choice="required"
            )
            print("Gpt response: ", gpt_response)
            # Check that it's valid
            response = gpt_response.choices[0].message.tool_calls[0].function.arguments
            response = ast.literal_eval(response)
            response = response['chosen_action']
            if response in all_options:
                return response
        # Set the response to something random from the available commands
        return np.random.choice(all_options)
    except Exception as e:
        print("Exception: ", e)
        print("Sad")
        raise Exception("Failed to get text.")