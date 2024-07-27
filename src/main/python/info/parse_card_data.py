import json

def parse_card_data(input_data):
    cards = {}
    for line in input_data.strip().split('\n'):
        parts = line.split('\t')
        name = parts[0]
        name = name.lower()
        card_type = parts[1]
        rarity = parts[2]
        cost = parts[3]
        effect = parts[4]
        
        card_data = {
            "type": card_type,
            "rarity": rarity,
            "cost": cost
        }
        
        if '(' in cost:
            cost, upgraded_cost = cost.split(' ')
            cost = cost.strip('()')
            upgraded_cost = upgraded_cost.strip('()')
            card_data["cost"] = cost
            card_data["upgraded_cost"] = upgraded_cost
        else:
            card_data["cost"] = cost

        effects = effect.split('\t')
        card_data["effect"] = effects[0].strip()
        
        if len(effects) > 1:
            card_data["upgraded_effect"] = effects[1].strip()
        
        cards[name] = card_data
    
    return cards

if __name__ == "__main__":
    # Input data from ironclad_cards.txt
    input_file = open("colorless_cards.txt", "r")
    input_data = input_file.read()
    input_file.close()
    output_data = parse_card_data(input_data)
    # Write to ironclad_cards.json
    output_file = open("colorless_cards.json", "w")
    output_file.write(json.dumps(output_data, indent=4))