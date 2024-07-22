import sqlite3
import pandas as pd

def get_relic_by_name(relic_name):
    db_path = 'slay_the_spire_relics_cards.db'
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM Relics WHERE LOWER(Name) = ?"
    result = pd.read_sql_query(query, conn, params=(relic_name.lower(),))
    conn.close()
    if result.empty:
        return None
    return "Description: " + result['Description'].values[0]

def get_card_by_name(card_name):
    db_path = 'slay_the_spire_relics_cards.db'
    # If card is upgraded, remove the upgrade suffix
    upgrade = False
    if "+" in card_name:
        card_name = card_name.replace("+", "")
        upgrade = True
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM Cards WHERE Name = ?"
    result = pd.read_sql_query(query, conn, params=(card_name,))
    conn.close()
    # Return the Description and Rarity as a string
    if not result.empty:
        description = result['Description'].values[0]
        rarity = result['Rarity'].values[0]
        if upgrade:
            description += " (Upgraded)"
        return f"Description: {description} Rarity: {rarity}"
    return None

def get_card_rarity_by_name(card_name):
    db_path = 'slay_the_spire_relics_cards.db'
    conn = sqlite3.connect(db_path)
    query = "SELECT Rarity FROM Cards WHERE Name = ?"
    result = pd.read_sql_query(query, conn, params=(card_name,))
    conn.close()
    if result.empty:
        return "Uncommon"
    return result['Rarity'].values[0]

def get_relic_rarity_by_name(relic_name):
    db_path = 'slay_the_spire_relics_cards.db'
    conn = sqlite3.connect(db_path)
    query = "SELECT Rarity FROM Relics WHERE LOWER(Name) = ?"
    result = pd.read_sql_query(query, conn, params=(relic_name.lower(),))
    conn.close()
    if result.empty:
        return "Uncommon"
    return result['Rarity'].values[0]

# Example usage
'''
relic_name = 'vajra'
card_name = 'Bash'

relic_info = get_relic_by_name(relic_name)
card_info = get_card_by_name(card_name)

print("Relic Information:\n", relic_info)
print("\nCard Information:\n", card_info)

card_rarity = get_card_rarity_by_name(card_name)
relic_rarity = get_relic_rarity_by_name(relic_name)

print("\nCard Rarity:", card_rarity)
print("Relic Rarity:", relic_rarity)
'''
