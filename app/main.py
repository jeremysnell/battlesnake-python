import random
import bottle
import os
from pypaths import astar

# Turn a coord delta into a direction
# 0,0 is the top left of the map
DIRECTION_MAP = {
    (0, -1): 'up',
    (0, 1): 'down',
    (-1, 0): 'left',
    (1, 0): 'right'
}

TRAIT_OPPORTUNISTIC = 'opp'
TRAIT_AGGRESSIVE = 'agg'
TRAIT_GLUTTONOUS = 'glu'
TRAIT_INSECURE = 'ins'

DNA = [
    10,     # BASE_COST
    100,    # HEAD_DANGER_COST
    300,    # FLOOD_DANGER_COST
    20,     # WALL_DANGER_COST
    -10,    # BODY_ADJACENT_COST
    100,    # MAX_COST_CONSIDERED_SAFE
    30,     # PECKISH_THRESHOLD
    10,     # STARVING_THRESHOLD
    20      # MAX_OPPORTUNISTIC_EAT_COST
]

# Algorithm constants
BASE_COST = DNA[0]
HEAD_DANGER_COST = DNA[1]
FLOOD_DANGER_COST = DNA[2]
WALL_DANGER_COST = DNA[3]
BODY_ADJACENT_COST = DNA[4]
MAX_COST_CONSIDERED_SAFE = DNA[5]

PECKISH_THRESHOLD = DNA[6]
STARVING_THRESHOLD = DNA[7]
MAX_OPPORTUNISTIC_EAT_COST = DNA[8]


# Add two coord tuples together
def add_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x + y, coord_one, coord_two))


# Find the difference between two coord tuples
def sub_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x - y, coord_one, coord_two))


# Convert from x,y point dictionary to coord tuple
def point_to_coord(point):
    return point['x'], point['y']


# Returns the cheapest path to a coord, using the astar algorithm
def get_path_to_coord(finder, head_coord, target_coord):
    path = finder(head_coord, target_coord)
    return path if path[0] else None


# Returns the shortest paths to each point, using the astar algorithm
def get_paths_to_coords(finder, head_coord, target_coords):
    return [path for path in [finder(head_coord, coord) for coord in target_coords] if path[0]]


# Returns the shortest paths to each point, using the astar algorithm
def get_paths_to_points(finder, head_coord, target_points):
    return get_paths_to_coords(finder, head_coord, [point_to_coord(point) for point in target_points])


# Get the four neighboring squares for a given coord (up, down, left, right)
def get_coord_neighbors(coord):
    return [add_coords(coord, dir_coord) for dir_coord in DIRECTION_MAP.keys()]


# Is the given coord adjacent to any of the given coords?
def is_adjacent_to_coords(coord, coords):
    return any([neighbor for neighbor in get_coord_neighbors(coord) if neighbor in coords])


# Find non-fatal node neighbors
def get_valid_neighbors(coord, map_size, fatal_coords, my_head, my_tail):

    # Possible neighbors of input coords
    coord_neighbors = get_coord_neighbors(coord)

    valid_neighbors = [
        neighbor for neighbor in coord_neighbors
        if 0 <= neighbor[0] < map_size[0]       # X Coord must be within map
        and 0 <= neighbor[1] < map_size[1]      # Y Coord must be within map
        and (neighbor not in fatal_coords       # Don't crash into any snake
             or (coord != my_head and neighbor == my_tail))      # Our tail is only invalid if we're adjacent
    ]

    return valid_neighbors


# Node cost calculation, which will make more dangerous paths cost more
def get_cost(coord1, coord2, map_size, head_danger_coords, coord_to_fill_danger, im_trapped, my_body, my_length):
    # Cost is weighted towards squares in the center, since these are safer(?)
    # cost = (abs(coord2[0] - map_size[0] / 2) + abs(coord2[1] - map_size[1] / 2)) * 2
    cost = BASE_COST

    # If we're trapped, we need to pack tightly, so we'll try and go next to our body
    if im_trapped and is_adjacent_to_coords(coord2, my_body):
        cost += BODY_ADJACENT_COST

    # Pathing near walls costs more
    if coord2[0] == 0 or coord2[0] == map_size[0] - 1:
        cost += WALL_DANGER_COST
    if coord2[1] == 0 or coord2[1] == map_size[1] - 1:
        cost += WALL_DANGER_COST

    # Pathing into squares adjacent to a snake head costs much more
    if coord2 in head_danger_coords:
        cost += HEAD_DANGER_COST

    # Pathing into squares in an area smaller than ourselves costs more, relative to how small
    if coord2 in coord_to_fill_danger.keys():
        cost += (1 - (coord_to_fill_danger[coord2] / my_length)) * FLOOD_DANGER_COST

    return cost


# Determines the size of the safe area around a coord
def flood_fill(start_coord, neighbor_func, max_size=None):
    explored = []
    queue = [start_coord]
    while queue:
        next_coord = queue.pop(0)
        explored.append(next_coord)

        if max_size and len(explored) == max_size:
            return explored

        neighbors = neighbor_func(next_coord)
        for neighbor in neighbors:
            if neighbor not in queue and neighbor not in explored:
                queue.append(neighbor)

    return explored


@bottle.post('/move')
@bottle.post('/<traits>/move')
def move(traits=''):
    data = bottle.request.json

    # Snake behavior controls
    snake_traits = traits.split('-')

    map_size = (data['width'], data['height'])

    # Our snake's data
    my_id = data['you']['id']
    my_length = data['you']['length']
    my_health = data['you']['health']
    my_coords = [point_to_coord(point) for point in data['you']['body']['data']]
    my_head = my_coords[0]
    my_body = my_coords[1:-1] if my_length > 2 else []
    my_tail = my_coords[-1]

    # Avoid squares that will kill us
    fatal_coords = [point_to_coord(point) for snake in data['snakes']['data'] for point in snake['body']['data']]
    
    # Used by the astar algorithm to evaluate path nodes
    def neighbors_func(node):
        return get_valid_neighbors(node, map_size, fatal_coords, my_head, my_tail)

    # Are we the longest snake?
    im_longest = my_length > max([snake['length'] for snake in data['snakes']['data']])

    # Avoid squares adjacent to enemy snake heads, since they're dangerous
    # Unless we're longer than them, then we're safe
    bigger_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data'] if snake['id'] != my_id and snake['length'] >= my_length]
    head_danger_coords = [neighbor for head in bigger_snake_heads for neighbor in get_coord_neighbors(head)]

    # Get valid moves
    valid_moves = neighbors_func(my_head)

    # TODO: Weight based on relative size of flood fill areas?
    # TODO: Weight so open space is better than corridors?
    # TODO: Make snake head predictions for next turn? Are we going to be trapped?
    # TODO: Add food distance calcs?
    # TODO: Go after food we're closed to?

    # Find the size of the area we'd be moving into, for each valid move
    fill_coords = dict([(move_coord, flood_fill(move_coord, neighbors_func, my_length)) for move_coord in valid_moves])

    # If the area is smaller than our size, it's dangerous
    coord_to_fill_danger = dict([(coord, len(fill)) for coord, fill in fill_coords.items() if len(fill) < my_length])

    # We're enclosed in an area smaller than our body
    im_trapped = len(coord_to_fill_danger) == len(fill_coords)

    # Used by the astar algorithm to evaluate node costs
    def cost_func(node1, node2):
        return get_cost(node1, node2, map_size, head_danger_coords, coord_to_fill_danger, im_trapped, my_body, my_length)

    # Create the astar path finder
    finder = astar.pathfinder(neighbors=neighbors_func, cost=cost_func)

    next_path = []

    # Find paths to all possible food, that we can reach in time
    food_paths = [path for path in get_paths_to_points(finder, my_head, data['food']['data']) if len(path[1]) <= my_health]

    # Let's follow the cheapest path
    best_food_path = min(food_paths, key=lambda x: x[0]) if food_paths else None

    # Eat food if it's close or we're hungry
    if best_food_path and ((TRAIT_OPPORTUNISTIC in snake_traits and best_food_path[0] <= MAX_OPPORTUNISTIC_EAT_COST)
                           or (my_health < PECKISH_THRESHOLD and best_food_path[0] < MAX_COST_CONSIDERED_SAFE)
                           or my_health < STARVING_THRESHOLD):
        next_path = best_food_path

    # The bigger snakes eat the little ones
    # Path to a small snake's head neighbor
    if not next_path and TRAIT_AGGRESSIVE in snake_traits:
        smaller_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data'] if snake['length'] < my_length]
        smaller_snake_targets = [neighbor for head in smaller_snake_heads for neighbor in get_coord_neighbors(head)]
        attack_paths = get_paths_to_coords(finder, my_head, smaller_snake_targets)
        best_attack_path = min(attack_paths, key=lambda x: x[0]) if attack_paths else None

        if best_attack_path and best_attack_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = best_attack_path

    # Try and get longer
    if not next_path and TRAIT_GLUTTONOUS in snake_traits:
        if best_food_path and not im_longest and best_food_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = best_food_path

    # Try and chase tail
    if not next_path and TRAIT_INSECURE in snake_traits:
        tail_path = get_path_to_coord(finder, my_head, my_tail)

        if tail_path and tail_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = tail_path

    # Move to the safest adjacent square
    if not next_path:
        valid_move_costs = [(cost_func(my_head, coord), coord) for coord in valid_moves]
        next_coord = min(valid_move_costs, key=lambda x: x[0])[1] if valid_move_costs else None

        # Uh oh, we found no valid moves. Randomly move to our death!
        if not next_coord:
            return {
                'move': random.choice(DIRECTION_MAP.values()),
                'taunt': 'Uh oh'
            }
    else:
        # Our target will be the second coord in the shortest path (the first coord is our current position)
        next_coord = next_path[1][1]

        print 'Target: %s - Cost: %s' % (next_path[1][-1], next_path[0])

    # Calculate to the change between our head and the next move
    coord_delta = sub_coords(next_coord, my_head)

    # Look up the name of the direction we're trying to move
    direction = DIRECTION_MAP[coord_delta]

    return {
        'move': direction,
        'taunt': direction
    }


@bottle.route('/')
@bottle.route('/<traits>')
@bottle.route('/<traits>/')
def static(traits=''):
    return "the server is running"


@bottle.route('/static/<path:path>')
@bottle.route('/<traits>/static/<path:path>')
def static(path, traits=''):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
@bottle.post('/<traits>/start')
def start(traits=''):
    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    # Company pride
    s4_colors = {
        'indigo': '#4E54A4',
        'green': '#44B5AD',
        'orange': '#F37970',
        'purple': '#AA66AA'
    }

    # Make us pretty!
    color = random.choice(s4_colors.values())

    return {
        'color': color,
        'taunt': 'SsSsSsS',
        'head_url': head_url,
        'name': 'battlesnake-python'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        # host=os.getenv('IP', '10.4.19.137'),
        host=os.getenv('IP', '192.168.0.19'),
        port=os.getenv('PORT', '8080'),
        debug=True)
