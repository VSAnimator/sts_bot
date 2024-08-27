from openai import OpenAI
import json
import numpy as np
import ast
import os
from groq import Groq
from wiki_info import get_relic_by_name, get_card_by_name
import copy

MODEL = 'gpt-4o' #'llama3-70b-8192'

# Read the system prompt from the file system.txt
with open('prompts/system.txt', 'r') as file:
    system_prompt = file.read()

# Load v2 system prompt
with open('prompts/system_v2.txt', 'r') as file:
    system_prompt_v2 = file.read()

# Load v3 system prompt
with open('prompts/system_v3.txt', 'r') as file:
    system_prompt_v3 = file.read()

def get_text_v3(prompt, session_id, similar_states, human_test=False):
    # Set up the client with helicone logging
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"{session_id}"
        }
    )
    '''
    client = Groq(
        api_key="",
        base_url="https://groq.helicone.ai",
        default_headers={
            "Helicone-Auth": f"Bearer {os.environ.get('HELICONE_API_KEY')}",
        }
    )
    '''

    try:
        # Get the valid options out of the prompt
        if human_test:
            all_options = prompt['available_commands']
            del prompt['available_commands']
            del prompt['choice_list']
            # Augment system prompt with task-specific information
            act_id = prompt['act']
            screen_type = prompt['screen_type']
        else:
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

        joe_advice = None
        if screen_type == "CARD_REWARD":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_cards.txt"
        elif screen_type == "SHOP_SCREEN":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_merchant.txt"
        elif screen_type == "MAP":
            custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_pathing.txt"
        elif screen_type == "GRID":
            if 'game_state' not in prompt or prompt['game_state']['screen_state']['for_upgrade'] == True:
                custom_file_name = "prompts/sub_prompts/act" + str(act_id) + "_upgrades.txt"
            else:
                custom_file_name = None
        elif screen_type == "EVENT" and prompt['game_state']['screen_state']['event_id'] == "Neow Event":
            custom_file_name = "prompts/sub_prompts/neow.txt"
        else:
            custom_file_name = None
        if custom_file_name:
            with open(custom_file_name, 'r') as file:
                joe_advice = file.read()
            if screen_type == "MAP":
                joe_advice = joe_advice + "\n" + "For each pathing option, 'expanded_next_nodes' contains a condensed representation of all the nodes you will have to visit before the next pathing decision. Use this to help decide which path to take." 

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

        print("System prompt: ", system_prompt_v3)

        # Temporary test
        #system_prompt_custom = system_prompt

        for i in range(3):
            if i > 0:
                print("Retrying...")
            prompt = prompt + "\n" + "Evaluate the current deck and relics in the context of the current game state (Ascension, Floor, Boss, etc.) along the following dimensions: attack, defense, scaling, synergies, card draw. Return a 1-2 sentence evaluation for each dimension."
            current_messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt_v3}]},
                #{"role": "system", "content": system_prompt_custom},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
                #{"role": "user", "content": prompt}
            ]
            gpt_response = client.chat.completions.create(
                model=MODEL,
                messages=current_messages,
            )
            # Add the response to the current_messages
            current_messages.append({"role": "assistant", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})

            # This will be re-used across all the branches
            deck_analysis_messages = copy.deepcopy(current_messages)

            # Zero-shot messages
            zero_shot_messages = copy.deepcopy(current_messages)

            #current_messages.append({"role": "system", "content": gpt_response.choices[0].message.content})
            # Evaluate each of the current options
            prompt = "Evaluate each of the choices available in context of the current deck and relics, considering how each choice contributes to both the short-term (defeating coming enemies) and the long-term (defeating the Act boss). Return a 1-2 sentence evaluation for each choice." + "\n"

            # Let's add some wiki info on each choice
            key_choice_info = "Choices available: " + str(all_options)
            if screen_type == "BOSS_REWARD":
                # Add key info
                key_choice_info += "Don't worry about the current hp; since the boss battle has just been completed, you will be healed immediately after this reward is selected. \n"
            '''
                key_choice_info += "Key information on each choice: "
                for choice in all_options:
                    added_info = get_relic_by_name(choice)
                    if added_info:
                        key_choice_info += "\n" + choice + ": " + added_info
            elif screen_type == "CARD_REWARD":
                # Add key info
                key_choice_info += "\n" + "Key information on each choice: "
                for choice in all_options:
                    added_info = get_card_by_name(choice)
                    if added_info:
                        key_choice_info += "\n" + choice + ": " + added_info
            '''

            prompt += key_choice_info

            zero_shot_response = None
            if not similar_states and not joe_advice:
                zero_shot_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                #current_messages.append({"role": "user", "content": prompt})
                # Again call GPT
                gpt_response = client.chat.completions.create(
                    model=MODEL,
                    messages=zero_shot_messages,
                )
                zero_shot_messages.append({"role": "assistant", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})
                #current_messages.append({"role": "system", "content": gpt_response.choices[0].message.content})

                # Chose one of the options given zero-shot eval
                prompt = "Given this evaluation, which of the choices is the best choice to take to maximize the chances of winning the run? Give an 1-2 sentence explanation for your choice, and also provide 1 sentence explaining your confidence level in the choice and whether there are any other high-quality options"
                zero_shot_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                #current_messages.append({"role": "user", "content": prompt})
                zero_shot_response = client.chat.completions.create(
                    model=MODEL,
                    messages=zero_shot_messages,
                    #tools=tools,
                    #tool_choice="required"
                )

            human_analysis_response = None
            if similar_states:
                # Start from the deck analysis
                human_analysis_messages = copy.deepcopy(deck_analysis_messages)

                if len(similar_states) == 2 and similar_states[1] is None:
                    similar_states = similar_states[0]
                # Reason across the similar states to make a decision
                if len(similar_states) == 2:
                    # We have wins and losses
                    prompt = "To help your decision, here are up to 5 potentially-similar states from a database of winning human playthroughs, and up to 5 from a database of losing human playthroughs. The 'actions taken' field annotates the choices the human made at a particular state. \n Winning: " + str(similar_states[0][:5]) + " \nLosing: " + str(similar_states[1][:5])
                else:
                    prompt = "To help your decision, here are up to 5 potentially-similar states from a database of winning human playthroughs, where the 'actions taken' field annotates the choices the human made at a particular state: " + str(similar_states[:5])
                prompt += "\n" + "1. Analyze each state, particularly the deck and relics, and compare them to the current state. Provide two sentences of analysis per state. 2. What can be learned from the decisions humans made in these states? Place particular emphasis on states that are very similar to the current state."
                human_analysis_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                #current_messages.append({"role": "user", "content": prompt})
                gpt_response = client.chat.completions.create(
                    model=MODEL,
                    messages=human_analysis_messages,
                )
                human_analysis_messages.append({"role": "assistant", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})
                #current_messages.append({"role": "system", "content": gpt_response.choices[0].message.content})

                prompt = key_choice_info + "Given the evaluation of the deck and of similar states, which of the choices is the best choice to take to maximize the chances of winning the run? 1. Make a choice, 2. Provide 1 sentence explaining your confidence level in the choice and whether there are any other high-quality options."
                human_analysis_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                #current_messages.append({"role": "user", "content": prompt})
                human_analysis_response = client.chat.completions.create(
                    model=MODEL,
                    messages=human_analysis_messages,
                    #tools=tools,
                    #tool_choice="required"
                )

            joe_response = None
            if joe_advice:
                # Make a choice based on Joe's advice
                joe_messages = copy.deepcopy(deck_analysis_messages)
                joe_messages.append({"role": "user", "content": [{"type": "text", 
                    "text": key_choice_info + "Here is some advice from Joe, an expert player: " + joe_advice + "Given the evaluation of the deck and Joe's advice, which of the choices is the best choice to take to maximize the chances of winning the run? 1. Make a choice, 2. Provide 1 sentence explaining your confidence level in the choice and whether there are any other high-quality options."}]})

                joe_response = client.chat.completions.create(
                    model=MODEL,
                    messages=joe_messages,
                    #tools=tools,
                    #tool_choice="required"
                )

            # Chose one of the options
            decision_messages = copy.deepcopy(deck_analysis_messages)
            prompt = "Given the current game state, you have to choose to take one of the following actions: " + str(all_options) + "\n"
            if not human_analysis_response and not joe_response:
                prompt += "A zero-shot analyis of the choices: " + zero_shot_response.choices[0].message.content + "\n"
            if human_analysis_response:
                prompt += "An analysis of the choices based off similar states from successful human playthroughs: " + human_analysis_response.choices[0].message.content + "\n"
            if joe_response:
                prompt += "An analysis of the choices based off advice from an expert player: " + joe_response.choices[0].message.content + "\n"
            prompt += "Which of the choices is the best choice to take to maximize the chances of winning the run?"
            current_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
            #current_messages.append({"role": "user", "content": prompt})
            gpt_response = client.chat.completions.create(
                model=MODEL,
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

def text_grad(filename):
    #filename = "1718306208.303196"

    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"grad_{filename}"
        }
    )

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

    # Parse the final state and get the floor, score, and victory true/false
    print("Final state: ", final_state)
    #final_state = ast.literal_eval(final_state)
    #floor = final_state['game_state']['floor']
    #score = final_state['game_state']['screen_state']['score']
    #victory = final_state['game_state']['screen_state']['victory']

    # Run gpt eval on the final state
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": "You are evaluating the final state of a playthrough of Slay the Spire. You will be provided the end state of a run through the game. In three sentences, describe changes to the state (deck, relics, etc.), if any, that could have improved the outcome of the run."}],},
            {"role": "user", "content": [{"type": "text", "text": final_state}]}
        ],
    )

    output_state_eval = response.choices[0].message.content

    #output_state_eval = "Floor: " + str(floor) + ", Score: " + str(score) + ", Victory: " + str(victory)
    print("Output state evaluation: ", output_state_eval)
    # Now loop through the trajectory and analyze each decision
    for i in range(len(trajectory) - 3, -1, -1):
        try:
            state = trajectory[i]
            # Check if its a bot action
            if "Bot response: " not in state:
                continue
            # Now put together prompt as last two elements of trajectory
            #prompt = "Evaluate this decision by the metagame bot: " + trajectory[i - 1] + "\n" + trajectory[i]
            #print("Prompt: ", prompt)

            # Input state
            input_state = trajectory[i - 1]

            # Decision
            decision = trajectory[i].split("Bot response: ")[1]

            # Output state
            output_state = trajectory[i + 1]

            print("Input state: ", input_state)
            print("Decision: ", decision)
            print("Output state: ", output_state)

            prompt = "Evaluate this decision by the metagame bot: \n Input state X: " + input_state + "\n Decision Y: " + decision + "\n Evaluation of output state Z: " + output_state_eval

            # We need the "choice_list" from the input state
            input_state = ast.literal_eval(input_state)
            choice_list = input_state['game_state']['choice_list']
            
            print("Choice list: ", choice_list)

            # Create tool
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "evaluate_decision_and_changes_to_input",
                        "description": "Evaluate how both the decision made and the input state could've been altered to address the evaluation of the output state",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "evaluation_of_action_Y": {"type": "string", "description": "One-sentence evaluation of the action Y taken"},
                                "best_action": {
                                    "type": "string",
                                    "description": "Best action y that could've been taken from the choice list",
                                    "enum": choice_list
                                },
                                "changes_to_input_state": {"type": "string", "description": "In three sentences, describe changes to the state X (deck, relics, etc.), if any, that could have address the evaluation of the output state Z. "},
                            },
                            "required": ["evaluation_of_action_taken", "best_action", "changes_to_input_state"],
                        },
                    },
                }
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                tools=tools,
                tool_choice="required"
            )
            print("Response: ", response.choices[0].message.tool_calls)

            # Update the output_state_eval
            output_state_eval = ast.literal_eval(response.choices[0].message.tool_calls[0].function.arguments)['changes_to_input_state']
            print("Output state evaluation: ", output_state_eval)
            #split_response = json.dumps(response.choices[0].message.tool_calls[0].function.arguments)
            # Strip all newline chars from response
            #stripped_response = str(response.choices[0].message.tool_calls[0].function.arguments).replace("\n", "")
            #write_file.write(stripped_response + "\n")
        except Exception as e:
            print("Exception: ", e)
            write_file.write("Failed to get text.\n")
            exit()

def win_prediction(system_prompt, state, similar_states, run_id):
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"win_pred_{run_id}"
        }
    )

    prompt = "State to evaluate: " + json.dumps(state) + "\n" + "Similar states: " + str(similar_states) + "\n" + "Return both 'thought_process' and 'predicted_outcome'" 

    '''
    tool = {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": "Predict the outcome of the final boss battle for Slay the Spire",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_process": {
                        "type": "string",
                        "description": "A step-by-step thought process on how to evaluate the win probability of the state"
                    },
                },
                "required": ["thought_process"]
            }
        }
    }
    '''

    tool2 = {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": "Predict the outcome of the final boss battle for Slay the Spire",
            "parameters": {
                "type": "object",
                "properties": {
                    "predicted_outcome": {
                        "type": "string",
                        "description": "0 for a loss, 1 for a win",
                        "enum": ["0", "1"]
                    }
                },
                "required": ["predicted_outcome"]
            }
        }
    }

    response1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
    )

    # Append response to conversation, call tool2 to get final prediction
    response2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
            {"role": "assistant", "content": response1.choices[0].message.content},
            {"role": "user", "content": [{"type": "text", "text": "Given the thought process, predict the outcome of the final boss battle for Slay the Spire"}]}
        ],
        tools=[tool2],
        tool_choice="required"
    )

    return system_prompt, {"thought_process": response1.choices[0].message.content, "predicted_outcome": ast.literal_eval(response2.choices[0].message.tool_calls[0].function.arguments)['predicted_outcome']}

def update_win_prediction_prompt(prompt, state, similar_states, response, feedback, run_id):
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"win_pred_grad_{run_id}"
        }
    )

    system_prompt = "You are a superhuman AI that learns from its own mistakes by updating its system prompt. You previously predicted outcomes of playthroughs of Slay the Spire, and you will be given feedback on these previous predictions. Using the feedback on prior decisions, you will then describe how to update your system prompt to improve your future predictions. Don't make the system prompt overly long."

    prompt = "Original prompt: " + prompt + "\n" + "State provided: " + json.dumps(state) + "\n" + "Similar states provided: " + str(similar_states) + "\nYour evaluation: " + response + "\n" + "Feedback on your evaluation:" + feedback + "\n Describe how to update your system prompt to improve your future predictions."

    tool = {
        "type": "function",
        "function": {
            "name": "update_system_prompt",
            "description": "Update the system prompt to address the feedback",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "string",
                        "description": "An analysis of how to update the system prompt, based off the feedback"
                    },
                    "new_prompt": {
                        "type": "string",
                        "description": "An updated system prompt",
                    }
                },
                "required": ["analysis", "new_prompt"]
            }
        }
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
        tools=[tool],
        tool_choice="required"
    )

    return response.choices[0].message.tool_calls[0].function.arguments

def state_comparison(system_prompt, state1, state2, run_id):
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"win_pred_{run_id}"
        }
    )

    prompt = "State 1: " + json.dumps(state1) + "\n" + "State 2: " + json.dumps(state2) + "\n" + "Return both 'thought_process' and 'predicted_outcome'" 

    '''
    tool = {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": "Predict the outcome of the final boss battle for Slay the Spire",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_process": {
                        "type": "string",
                        "description": "A step-by-step thought process on how to evaluate the win probability of the state"
                    },
                },
                "required": ["thought_process"]
            }
        }
    }
    '''

    tool2 = {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": "Predict the outcome of the final boss battle for Slay the Spire",
            "parameters": {
                "type": "object",
                "properties": {
                    "predicted_outcome": {
                        "type": "string",
                        "description": "1 if state 1 is better, or -1 if state 2 is better",
                        "enum": ["1", "-1", "0"]
                    }
                },
                "required": ["predicted_outcome"]
            }
        }
    }

    response1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
    )

    # Append response to conversation, call tool2 to get final prediction
    response2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
            {"role": "assistant", "content": response1.choices[0].message.content},
            {"role": "user", "content": [{"type": "text", "text": "Given the thought process, predict which state will do better in the final boss battle for Slay the Spire, or if both states will perform equally well. Output 1 if state 1 is better, or -1 if state 2 is better."}]}
        ],
        tools=[tool2],
        tool_choice="required"
    )

    return system_prompt, {"thought_process": response1.choices[0].message.content, "predicted_outcome": ast.literal_eval(response2.choices[0].message.tool_calls[0].function.arguments)['predicted_outcome']}

def update_state_comparison_prompt(prompt, state1, state2, response, feedback, run_id):
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"win_pred_grad_{run_id}"
        }
    )

    system_prompt = "You are a superhuman AI that learns from its own mistakes by updating its system prompt. You previously made predictions comparing outcomes of pairs of states from Slay the Spire, and you will be given feedback on these previous predictions. Using the feedback on prior decisions, you will then describe how to update your system prompt to improve your future predictions. Don't make the system prompt overly long."

    prompt = "Original prompt: " + prompt + "\n" + "State 1: " + json.dumps(state1) + "\n" + "State 2: " + json.dumps(state2) + "\nYour evaluation: " + response + "\n" + "Feedback on your evaluation:" + feedback + "\n Describe how to update your system prompt to improve your future predictions."

    tool = {
        "type": "function",
        "function": {
            "name": "update_system_prompt",
            "description": "Update the system prompt to address the feedback",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "string",
                        "description": "An analysis of how to update the system prompt, based off the feedback"
                    },
                    "new_prompt": {
                        "type": "string",
                        "description": "An updated system prompt",
                    }
                },
                "required": ["analysis", "new_prompt"]
            }
        }
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ],
        tools=[tool],
        tool_choice="required"
    )

    return response.choices[0].message.tool_calls[0].function.arguments

def value_decision(prompt, leaf_states, session_id):
    client = OpenAI(
        base_url="https://oai.hconeai.com/v1", 
        default_headers={ 
            "Helicone-Auth": f"Bearer {os.environ['HELICONE_API_KEY']}",
            "Helicone-Property-Session": f"{session_id}"
        }
    )

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
    
    system_prompt = "You are a superhuman AI evaluating the relative win probability of different leaf states from a monte carlo tree search of Slay the Spire. Evaluate each of the leaf states along following dimensions: hp, attack, defense, scaling, synergies, card draw. Each leaf state is reached by following a standard rollout policy after the current decision. Evaluate which of the states will perform the best, and use this to decide which action to take next. Think step by step." 

    # Augment system prompt with task-specific information
    prompt = "I have run a tree search to evaluate the following options: " + str(all_options) + "\n" + "Here is a dictionary of leaf states reached by the tree search: " + str(leaf_states) + "\n" + "Analyze each of the leaf states, and determine which ones is most likely to lead to a winning run."

    current_messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        #{"role": "system", "content": system_prompt_custom},
        {"role": "user", "content": [{"type": "text", "text": prompt}]}
        #{"role": "user", "content": prompt}
    ]

    gpt_response = client.chat.completions.create(
        model=MODEL,
        messages=current_messages,
    )
    # Add the response to the current_messages
    current_messages.append({"role": "assistant", "content": [{"type": "text", "text": gpt_response.choices[0].message.content}]})

    prompt = "Given the current game state, you have to choose to take one of the following actions: " + str(all_options) + "\n"
    prompt += "Which of the choices is the best choice to take to maximize the chances of winning the run?"
    current_messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
    #current_messages.append({"role": "user", "content": prompt})
    tools = [
        {
            "type": "function",
            "function": {
                "name": "choose_best_action",
                "description": "Choose the best action to take from a list of options",
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

    gpt_response = client.chat.completions.create(
        model=MODEL,
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
    else:
        print("Invalid response")
        return np.random.choice(all_options)