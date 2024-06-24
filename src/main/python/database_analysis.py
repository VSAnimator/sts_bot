import dataset
import json
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt

# Connect to the database
db_url = 'sqlite:///slay_the_spire.db'
db = dataset.connect(db_url)

print("Creating indices for faster queries...")

# Create indices for faster queries
with db as tx:
    tx.query('CREATE INDEX IF NOT EXISTS idx_ascension_level ON states (ascension_level)')
    tx.query('CREATE INDEX IF NOT EXISTS idx_play_id ON states (play_id)')

print("Indices created.")

# Fetch all records from the states table
table = db['states']
records = table.all()

# Convert records to a DataFrame
df = pd.DataFrame(records)

print("Data loaded.")

# 1. Distribution over ascensions
ascension_counts = df['ascension_level'].value_counts().sort_index()
print("Distribution over Ascensions:")
print(ascension_counts)

# Plotting the distribution over ascensions
plt.figure(figsize=(10, 5))
ascension_counts.plot(kind='bar')
plt.title('Distribution over Ascensions')
plt.xlabel('Ascension Level')
plt.ylabel('Count')
plt.show()

# 2. Cards most chosen and 3. Cards most skipped
chosen_cards = Counter()
offered_cards = Counter()
skipped_count = 0
total_choices = 0

for index, row in df.iterrows():
    actions_taken = json.loads(row['actions_taken'])
    for action in actions_taken:
        if 'Card picked' in action:
            total_choices += 1
            picked_info = action.split(", Cards not picked: ")
            picked_card = picked_info[0].split(": ")[1]
            not_picked_cards = picked_info[1].split(", ")
            
            if picked_card == 'SKIP':
                skipped_count += 1
            else:
                chosen_cards[picked_card] += 1
            
            for card in not_picked_cards:
                offered_cards[card] += 1
            if picked_card != 'SKIP':
                offered_cards[picked_card] += 1

# Calculate fractions
chosen_fractions = {card: chosen_cards[card] / offered_cards[card] for card in offered_cards}
skip_fraction = skipped_count / total_choices

# 4. Most popular relics
relics_counter = Counter()
for relics in df['relics']:
    relics_list = json.loads(relics)
    for relic in relics_list:
        relics_counter[relic] += 1

# Print results
print("\nCards Most Chosen:")
for card, count in chosen_cards.most_common(10):
    print(f"{card}: {count}")

print("\nCards Most Skipped:")
for card, count in Counter(offered_cards).most_common(10):
    if card not in chosen_cards:
        print(f"{card}: {count}")

print("\nMost Popular Relics:")
for relic, count in relics_counter.most_common(10):
    print(f"{relic}: {count}")

print("\nFraction of Times Each Card is Chosen When Available:")
for card, fraction in sorted(chosen_fractions.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"{card}: {fraction:.2f}")

print(f"\nFraction of the Time We Skip: {skip_fraction:.2f}")

# Print all counters
print("\nChosen Cards Counter:")
print(chosen_cards)
print("\nOffered Cards Counter:")
print(offered_cards)
print("\nRelics Counter:")
print(relics_counter)


# Plotting the most chosen and most skipped cards
plt.figure(figsize=(15, 5))

plt.subplot(1, 2, 1)
pd.Series(chosen_cards).sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Top 10 Most Chosen Cards')
plt.xlabel('Card')
plt.ylabel('Count')

plt.subplot(1, 2, 2)
pd.Series(offered_cards).sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Top 10 Most Offered Cards')
plt.xlabel('Card')
plt.ylabel('Count')

plt.show()

# Plotting the most popular relics
plt.figure(figsize=(10, 5))
pd.Series(relics_counter).sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Top 10 Most Popular Relics')
plt.xlabel('Relic')
plt.ylabel('Count')
plt.show()
