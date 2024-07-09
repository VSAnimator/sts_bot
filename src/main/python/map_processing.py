from collections import deque

def find_shortest_path_to_symbol(map_nodes, start_x, start_y, symbol):
    # Convert the map to a dictionary for easy lookup
    map_dict = {(node['x'], node['y']): node for node in map_nodes}

    # Initialize the BFS queue
    queue = deque([((start_x, start_y), [])])
    visited = set()

    while queue:
        (current_x, current_y), path = queue.popleft()

        current_node = map_dict.get((current_x, current_y))
        if current_node:
            # Check if we have reached a shop
            if map_dict[(current_x, current_y)]['symbol'] == symbol:
                return path + [(current_x, current_y)]

            # Mark the current node as visited
            visited.add((current_x, current_y))

            # Add the children to the queue
            for child in current_node['children']:
                child_coords = (child['x'], child['y'])
                if child_coords not in visited:
                    queue.append((child_coords, path + [(current_x, current_y)]))

    # Return an empty path if no shop is found
    return []

def traverse_map(map_nodes, start_x, start_y, symbol, depth):
    # Convert the map to a dictionary for easy lookup
    map_dict = {(node['x'], node['y']): node for node in map_nodes}

    # Initialize variables for tracking the path
    max_path = []
    min_path = []
    max_m_count = 0
    min_m_count = float('inf')

    # Depth-First Search (DFS) to find the path with maximum 'M' nodes
    def dfs(current_node, current_path, m_count, depth):
        nonlocal max_path, min_path, max_m_count, min_m_count

        current_path.append((current_node['x'], current_node['y']))
        if current_node['symbol'] == symbol:
            m_count += 1

        # Update the max path if the current one has more 'M' nodes
        if m_count > max_m_count and (depth == 1 or len(current_node['children']) == 0):
            max_m_count = m_count
            max_path = current_path.copy()
        if m_count < min_m_count and (depth == 1 or len(current_node['children']) == 0):
            min_m_count = m_count
            min_path = current_path.copy()

        # Traverse children nodes
        for child in current_node['children']:
            child_node = map_dict.get((child['x'], child['y']))
            if child_node and (child_node['x'], child_node['y']) not in current_path and depth > 1:
                dfs(child_node, current_path, m_count, depth - 1)

        # Backtrack
        current_path.pop()

    # Start DFS from each 'M' node
    start_node = map_dict.get((start_x, start_y))
    dfs(start_node, [], 0, depth)

    return max_path, min_path, max_m_count, min_m_count

'''
# Example usage:
map_nodes = [
    {"symbol": "M", "children": [{"x": 2, "y": 1}], "x": 2, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 1}], "x": 3, "y": 0, "parents": []},
    {"symbol": "M", "children": [{"x": 6, "y": 1}], "x": 6, "y": 0, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 2}, {"x": 3, "y": 2}], "x": 2, "y": 1, "parents": []},
    {"symbol": "$", "children": [{"x": 5, "y": 2}], "x": 4, "y": 1, "parents": []},
    {"symbol": "?", "children": [{"x": 5, "y": 2}], "x": 6, "y": 1, "parents": []},
    {"symbol": "?", "children": [{"x": 2, "y": 3}], "x": 2, "y": 2, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 3}], "x": 3, "y": 2, "parents": []},
    {"symbol": "?", "children": [{"x": 4, "y": 3}, {"x": 5, "y": 3}, {"x": 6, "y": 3}], "x": 5, "y": 2, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 4}, {"x": 2, "y": 4}], "x": 2, "y": 3, "parents": []},
    {"symbol": "?", "children": [{"x": 3, "y": 4}], "x": 4, "y": 3, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 4}, {"x": 6, "y": 4}], "x": 5, "y": 3, "parents": []},
    {"symbol": "$", "children": [{"x": 6, "y": 4}], "x": 6, "y": 3, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 5}], "x": 1, "y": 4, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 5}], "x": 2, "y": 4, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 5}], "x": 3, "y": 4, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 5}], "x": 4, "y": 4, "parents": []},
    {"symbol": "?", "children": [{"x": 5, "y": 5}, {"x": 6, "y": 5}], "x": 6, "y": 4, "parents": []},
    {"symbol": "E", "children": [{"x": 0, "y": 6}, {"x": 2, "y": 6}], "x": 1, "y": 5, "parents": []},
    {"symbol": "E", "children": [{"x": 3, "y": 6}, {"x": 4, "y": 6}], "x": 3, "y": 5, "parents": []},
    {"symbol": "E", "children": [{"x": 5, "y": 6}], "x": 5, "y": 5, "parents": []},
    {"symbol": "M", "children": [{"x": 6, "y": 6}], "x": 6, "y": 5, "parents": []},
    {"symbol": "R", "children": [{"x": 1, "y": 7}], "x": 0, "y": 6, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 7}], "x": 2, "y": 6, "parents": []},
    {"symbol": "$", "children": [{"x": 3, "y": 7}], "x": 3, "y": 6, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 7}], "x": 4, "y": 6, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 7}], "x": 5, "y": 6, "parents": []},
    {"symbol": "E", "children": [{"x": 5, "y": 7}], "x": 6, "y": 6, "parents": []},
    {"symbol": "M", "children": [{"x": 0, "y": 8}], "x": 1, "y": 7, "parents": []},
    {"symbol": "R", "children": [{"x": 1, "y": 8}], "x": 2, "y": 7, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 8}], "x": 3, "y": 7, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 8}], "x": 4, "y": 7, "parents": []},
    {"symbol": "?", "children": [{"x": 6, "y": 8}], "x": 5, "y": 7, "parents": []},
    {"symbol": "T", "children": [{"x": 0, "y": 9}], "x": 0, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 1, "y": 9}], "x": 1, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 1, "y": 9}, {"x": 2, "y": 9}], "x": 2, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 3, "y": 9}], "x": 3, "y": 8, "parents": []},
    {"symbol": "T", "children": [{"x": 6, "y": 9}], "x": 6, "y": 8, "parents": []},
    {"symbol": "E", "children": [{"x": 1, "y": 10}], "x": 0, "y": 9, "parents": []},
    {"symbol": "E", "children": [{"x": 1, "y": 10}], "x": 1, "y": 9, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 10}], "x": 2, "y": 9, "parents": []},
    {"symbol": "M", "children": [{"x": 2, "y": 10}], "x": 3, "y": 9, "parents": []},
    {"symbol": "?", "children": [{"x": 6, "y": 10}], "x": 6, "y": 9, "parents": []},
    {"symbol": "M", "children": [{"x": 0, "y": 11}, {"x": 1, "y": 11}], "x": 1, "y": 10, "parents": []},
    {"symbol": "R", "children": [{"x": 1, "y": 11}], "x": 2, "y": 10, "parents": []},
    {"symbol": "E", "children": [{"x": 6, "y": 11}], "x": 6, "y": 10, "parents": []},
    {"symbol": "?", "children": [{"x": 0, "y": 12}], "x": 0, "y": 11, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 12}, {"x": 2, "y": 12}], "x": 1, "y": 11, "parents": []},
    {"symbol": "M", "children": [{"x": 6, "y": 12}], "x": 6, "y": 11, "parents": []},
    {"symbol": "M", "children": [{"x": 0, "y": 13}], "x": 0, "y": 12, "parents": []},
    {"symbol": "R", "children": [{"x": 0, "y": 13}, {"x": 2, "y": 13}], "x": 1, "y": 12, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 13}], "x": 2, "y": 12, "parents": []},
    {"symbol": "R", "children": [{"x": 5, "y": 13}], "x": 6, "y": 12, "parents": []},
    {"symbol": "M", "children": [{"x": 1, "y": 14}], "x": 0, "y": 13, "parents": []},
    {"symbol": "?", "children": [{"x": 1, "y": 14}], "x": 2, "y": 13, "parents": []},
    {"symbol": "M", "children": [{"x": 3, "y": 14}], "x": 3, "y": 13, "parents": []},
    {"symbol": "M", "children": [{"x": 4, "y": 14}], "x": 5, "y": 13, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 1, "y": 14, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 3, "y": 14, "parents": []},
    {"symbol": "R", "children": [{"x": 3, "y": 16}], "x": 4, "y": 14, "parents": []}
]

path = traverse_map(map_nodes, 3, 0, "M", 5)
print("Path with maximum 'M' nodes:", path[0], "min", path[1])
print("Max count", path[2], "min", path[3])

shop_path = find_shortest_path_to_symbol(map_nodes, 3, 0, "$")
print("Shortest path to shop:", shop_path)
'''