# Define the map as a list of dictionaries
map_data = [
    {"symbol": "M", "children": [{"x": 0, "y": 1}], "x": 0, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 1}], "x": 1, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 1}], "x": 2, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 1}], "x": 3, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 5, "y": 1}], "x": 6, "y": 0, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 2}], "x": 0, "y": 1, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 2}], "x": 2, "y": 1, "parents": []},
    {"symbol": "?", "children": [{"x": 3, "y": 2}], "x": 3, "y": 1, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 2}, {"x": 5, "y": 2}], "x": 4, "y": 1, "parents": []},
    {"symbol": "$", "children": [{"x": 6, "y": 2}], "x": 5, "y": 1, "parents": []},
    {"symbol": "M", "children": [{"x": 0, "y": 3}], "x": 1, "y": 2, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 3}], "x": 2, "y": 2, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 3}], "x": 3, "y": 2, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 3}], "x": 5, "y": 2, "parents": []},
    {"symbol": "?", "children": [{"x": 5, "y": 3}], "x": 6, "y": 2, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 4}], "x": 0, "y": 3, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 4}], "x": 1, "y": 3, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 4}], "x": 2, "y": 3, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 4}], "x": 4, "y": 3, "parents": []},
    {"symbol": "M", "children": [{"x": 5, "y": 4}], "x": 5, "y": 3, "parents": []},
    {"symbol": "?", "children": [{"x": 0, "y": 5}], "x": 1, "y": 4, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 5}, {"x": 2, "y": 5}], "x": 2, "y": 4, "parents": []},
    {"symbol": "$", "children": [{"x": 3, "y": 5}], "x": 4, "y": 4, "parents": []},
    {"symbol": "M", "children": [{"x": 5, "y": 5}], "x": 5, "y": 4, "parents": []},
    {"symbol": "E", "children": [{"x": 0, "y": 6}], "x": 0, "y": 5, "parents": []},
    {"symbol": "R", "children": [{"x": 1, "y": 6}, {"x": 2, "y": 6}], "x": 1, "y": 5, "parents": []},
    {"symbol": "E", "children": [{"x": 2, "y": 6}], "x": 2, "y": 5, "parents": []},
    {"symbol": "E", "children": [{"x": 4, "y": 6}], "x": 3, "y": 5, "parents": []},
    {"symbol": "R", "children": [{"x": 6, "y": 6}], "x": 5, "y": 5, "parents": []},
    {"symbol": "R", "children": [{"x": 0, "y": 7}], "x": 0, "y": 6, "parents": []},
    {"symbol": "E", "children": [{"x": 1, "y": 7}], "x": 1, "y": 6, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 7}], "x": 2, "y": 6, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 7}], "x": 4, "y": 6, "parents": []},
    {"symbol": "M", "children": [{"x": 5, "y": 7}], "x": 6, "y": 6, "parents": []},
    {"symbol": "E", "children": [{"x": 0, "y": 8}], "x": 0, "y": 7, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 8}], "x": 1, "y": 7, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 8}, {"x": 3, "y": 8}], "x": 3, "y": 7, "parents": []},
    {"symbol": "?", "children": [{"x": 6, "y": 8}], "x": 5, "y": 7, "parents": []},
    {"symbol": "T", "children": [{"x": 0, "y": 9}], "x": 0, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 0, "y": 9}], "x": 1, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 1, "y": 9}], "x": 2, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 3, "y": 9}], "x": 3, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 5, "y": 9}], "x": 6, "y": 8, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 10}], "x": 0, "y": 9, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 10}], "x": 1, "y": 9, "parents": []},
    {"symbol": "?", "children": [{"x": 3, "y": 10}], "x": 3, "y": 9, "parents": []},
    {"symbol": "E", "children": [{"x": 5, "y": 10}], "x": 5, "y": 9, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 11}], "x": 1, "y": 10, "parents": []},
    {"symbol": "R", "children": [{"x": 2, "y": 11}], "x": 2, "y": 10, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 11}], "x": 3, "y": 10, "parents": []},
    {"symbol": "M", "children": [{"x": 6, "y": 11}], "x": 5, "y": 10, "parents": []},
    {"symbol": "E", "children": [{"x": 1, "y": 12}, {"x": 2, "y": 12}, {"x": 3, "y": 12}], "x": 2, "y": 11, "parents": []},
    {"symbol": "M", "children": [{"x": 6, "y": 12}], "x": 6, "y": 11, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 13}], "x": 1, "y": 12, "parents": []},
    {"symbol": "$", "children": [{"x": 1, "y": 13}, {"x": 3, "y": 13}], "x": 2, "y": 12, "parents": []},
    {"symbol": "?", "children": [{"x": 3, "y": 13}], "x": 3, "y": 12, "parents": []},
    {"symbol": "E", "children": [{"x": 5, "y": 13}], "x": 6, "y": 12, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 14}], "x": 1, "y": 13, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 14}], "x": 3, "y": 13, "parents": []},
    {"symbol": "M", "children": [{"x": 5, "y": 14}], "x": 5, "y": 13, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 2, "y": 14, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 4, "y": 14, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 5, "y": 14, "parents": []}
]

# Helper function to find a node by its coordinates
def find_node(x, y):
    for node in map_data:
        if node['x'] == x and node['y'] == y:
            return node
    return None

# Function to get the linear path until the next branching point
def get_path_until_branch(x, y):
    path = []
    current_node = find_node(x, y)
    while current_node and len(current_node['children']) == 1:
        path.append(current_node)
        x, y = current_node['children'][0]['x'], current_node['children'][0]['y']
        current_node = find_node(x, y)
    if current_node:
        path.append(current_node)
    return path

# Get the paths from each starting point at y=0
starting_points = [node for node in map_data if node['y'] == 0]
paths_from_starting_points = {}

for start in starting_points:
    paths_from_starting_points[(start['x'], start['y'])] = get_path_until_branch(start['x'], start['y'])

# Output the results
for start, path in paths_from_starting_points.items():
    print(f"Starting from node at {start}:")
    for node in path:
        print(f"  Node at ({node['x']}, {node['y']}) with symbol {node['symbol']}")
    print("\n")

for start, path in paths_from_starting_points.items():
    print(f"Starting from node at {start}:")
    print(str.join("",[node['symbol'] for node in path]))
    print("\n")