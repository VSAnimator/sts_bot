import os
import time
import zipfile
import string

# Goal of this file is to traverse the startstates folder and find files that are A10 and have saves past level 45

# Get list of filenames from "startstates/"
base_path = "/Users/sarukkai/Library/Application Support/Steam/steamapps/common/SlayTheSpire/SlayTheSpire.app/Contents/Resources/startstates/"
filenames = os.listdir(base_path)

valid_filenames = []
# Iterate through folders
for folder in filenames:
    # There are elements for each level: 00, 01, 02, etc
    # Check if 45 exists
    # Print the max folder name nested
    levels = os.listdir(base_path + folder)
    max_level = max(levels)
    #print("Max level: ", max_level)
    if os.path.exists(base_path + folder + "/45"):
        #print("Checking folder: ", folder)
        #print("Level 45 exists")
        #print("Max level: ", max_level)
        # Get the date created for the folder
        date_created = os.path.getctime(base_path + folder + "/45")
        # Print in mmddyyyy format
        # Format date_created
        date_created = time.strftime('%m%d%Y', time.localtime(date_created))
        # Make sure this is july 16th or later, before that I didn't have all the unlocks
        if date_created < "07162021":
            continue
        #print("Date created: ", date_created) 
        # Now check that there is an IRONCLAD.autosave in the saves folder
        if os.path.isfile(base_path + folder + "/45/saves/IRONCLAD.autosave"):
            print("Has the save file")
            print("Date created: ", date_created)
            # Get the max folder name nested
            valid_filenames.append(folder)
    #else:
        #print("No save past level 45: ", folder)

print("Valid filenames: ", valid_filenames)

# Write filenames to a file
with open("valid_filenames.txt", "w") as f:
    for elem in valid_filenames:
        f.write(elem + "\n")

'''
# Zip the folders corresponding to valid filenames into a single compressed archive
with zipfile.ZipFile("valid_folders_archive.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
    for folder in valid_filenames:
        folder_path = os.path.join(base_path, folder)
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Add the file to the zip archive
                zipf.write(file_path, os.path.relpath(file_path, base_path))
'''

def convert_seed_to_string(seed: int) -> str:
    """Converts numeric seed from run file to alphanumeric seed"""
    
    char_string = string.digits + string.ascii_uppercase
    # Remove 'O' from the char_string
    char_string = char_string.replace('O', '')
    # Convert to unsigned
    leftover = seed = seed + 2**64 if seed < 0 else seed
    char_count = len(char_string)
    result = []
    while leftover != 0:
        remainder = leftover % char_count
        leftover = leftover // char_count
        index = int(remainder)
        c = char_string[index]
        result.insert(0, c)
    stringSeed = ''.join(result)
    return stringSeed

# Loop through the runs folder and find the run corresponding to each seed
runs_base_path = "./runs_raw"
runs_filenames = os.listdir(runs_base_path)

# List to hold renamed files for adding to the archive
renamed_files = []

# Loop through files, read the seed, and check if it is in the valid_filenames list
for filename in runs_filenames:
    with open(os.path.join(runs_base_path, filename), "r") as f:
        lines = f.readlines()
        for line in lines:
            if "seed" in line:
                #print("Found seed line: ", line)
                seed = int(line.split("seed\":")[1].split(",")[0])
                seed_str = convert_seed_to_string(seed)
                if seed_str in valid_filenames:
                    print("Found seed in valid_filenames: ", seed_str)
                    print("Filename: ", filename)
                    # Rename the file with seed
                    new_filename = f"{seed_str}_{filename}"
                    new_filepath = os.path.join(runs_base_path, new_filename)
                    os.rename(os.path.join(runs_base_path, filename), new_filepath)
                    renamed_files.append(new_filepath)
                break

# Add renamed files to the existing archive
with zipfile.ZipFile("valid_folders_raw_archive.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
    for filepath in renamed_files:
        zipf.write(filepath, os.path.relpath(filepath, runs_base_path))

