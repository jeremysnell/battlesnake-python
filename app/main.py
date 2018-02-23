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

# Algorithm constants
DANGER_WEIGHT = 100
FLOOD_DANGER_WEIGHT = 25
WALL_NODE_WEIGHT = 5
HUNGER_THRESHOLD = 30
MAX_OPPORTUNISTIC_EAT_COST = 2


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
def get_paths_to_points(finder, head_coord, target_points):
    return [path for path in [finder(head_coord, coord) for coord in [point_to_coord(point) for point in target_points]] if path[0]]


# Get the four neighbouring squares for a given coord (up, down, left, right)
def get_coord_neighbours(coord):
    return [add_coords(coord, dir_coord) for dir_coord in DIRECTION_MAP.keys()]


# Find non-fatal node neighbours
def get_valid_neighbours(coord, map_size, fatal_coords, my_head, my_tail):

    # TODO: Don't go into a space smaller than your body, using flood fill

    # Possible neighbours of input coords
    coord_neighbors = get_coord_neighbours(coord)

    valid_neighbours = [
        neighbor for neighbor in coord_neighbors
        if 0 <= neighbor[0] < map_size[0]       # X Coord must be within map
        and 0 <= neighbor[1] < map_size[1]      # Y Coord must be within map
        and (neighbor not in fatal_coords       # Don't crash into any snake
             or (coord != my_head and neighbor == my_tail))     # Our tail is only invalid if we're adjacent
    ]

    return valid_neighbours


# Node cost calculation, which will make more dangerous paths cost more
def get_cost(coord1, coord2, map_size, head_danger_coords, coord_to_fill_danger):
    # Cost is weighted towards squares in the center, since these are safer(?)
    # cost = (abs(coord2[0] - map_size[0] / 2) + abs(coord2[1] - map_size[1] / 2)) * 2
    cost = 1

    # Pathing near walls costs more
    if coord2[0] == 0 or coord2[0] == map_size[0] - 1:
        cost += WALL_NODE_WEIGHT
    if coord2[1] == 0 or coord2[1] == map_size[1] - 1:
        cost += WALL_NODE_WEIGHT

    # Pathing into squares adjacent to a snake head costs much more
    if coord2 in head_danger_coords:
        cost += DANGER_WEIGHT

    # Pathing into squares in an area smaller than ourselves costs more, relative to how small
    cost += coord_to_fill_danger.get(coord2, 0)

    return cost


def flood_fill(start_coord, neighbour_func, max_size=None):
    explored = []
    queue = [start_coord]
    while queue:
        next_coord = queue.pop(0)
        explored.append(next_coord)

        if max_size and len(explored) == max_size:
            return explored

        neighbours = neighbour_func(next_coord)
        for neighbour in neighbours:
            if neighbour not in queue and neighbour not in explored:
                queue.append(neighbour)

    return explored


@bottle.post('/move')
def move():
    data = bottle.request.json

    map_size = (data['width'], data['height'])

    # Our snake's data
    my_coords = [point_to_coord(point) for point in data['you']['body']['data']]
    my_head = my_coords[0]
    my_tail = my_coords[-1]
    my_health = data['you']['health']
    my_length = data['you']['length']
    im_hungry = my_health < HUNGER_THRESHOLD

    # Avoid squares that will kill us
    fatal_coords = [point_to_coord(point) for snake in data['snakes']['data'] for point in snake['body']['data']]

    # Used by the astar algorithm to evaluate path nodes
    def neighbors_func(node):
        return get_valid_neighbours(node, map_size, fatal_coords, my_head, my_tail)

    # Who's the longest snake? Could be useful...
    longest_snake_length = max([snake['length'] for snake in data['snakes']['data'] if snake['id'] != data['you']['id']] or [None])

    # Are we the longest (with buffer)?
    im_longest = my_length > longest_snake_length + 1

    # Avoid squares adjacent to enemy snake heads, since they're dangerous
    # Unless we're the longest, then they're safe
    other_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data'] if snake['id'] != data['you']['id']]
    snake_head_neighbours = [neighbour for head in other_snake_heads for neighbour in get_coord_neighbours(head)]
    head_danger_coords = snake_head_neighbours if not im_longest else []

    # Get valid moves
    valid_moves = neighbors_func(my_head)

    # TODO: Weight based on relative size of flood fill areas?
    # TODO: Weight so open space is better than corridors?

    # Find the size of the area we'd be moving into, for each valid move
    fill_coords = dict([(move_coord, flood_fill(move_coord, neighbors_func, my_length)) for move_coord in valid_moves])

    # If the area is smaller than our size, assign a danger to it
    coord_to_fill_danger = dict([(coord, (my_length - len(fill)) * FLOOD_DANGER_WEIGHT) for coord, fill in fill_coords.items() if len(fill) < my_length])

    print coord_to_fill_danger

    # Used by the astar algorithm to evaluate node costs
    def cost_func(node1, node2):
        return get_cost(node1, node2, map_size, head_danger_coords, coord_to_fill_danger)

    # Create the astar path finder
    finder = astar.pathfinder(neighbors=neighbors_func, cost=cost_func)

    next_path = []

    # TODO: Once we're bigger than other snakes, go for their heads?

    # Find paths to all possible food
    food_paths = get_paths_to_points(finder, my_head, data['food']['data'])

    # Let's follow the cheapest path, as long as we can get there before dying
    best_food_path = min([path for path in food_paths if len(path[1]) <= my_health], key=lambda x: x[0]) if food_paths else None

    # Eat food if it's close, we're hungry, or we're short
    if best_food_path and (best_food_path[0] <= MAX_OPPORTUNISTIC_EAT_COST
                           or im_hungry
                           or (not im_longest and best_food_path[0] < DANGER_WEIGHT)):
        next_path = best_food_path

    # If we're not going after food, or can't find a path to any, just follow our tail
    if not next_path:
        next_path = get_path_to_coord(finder, my_head, my_tail)

    # Can't get to our tail safely, so move to the safest adjacent square
    if not next_path:
        valid_move_costs = [(coord, cost_func(my_head, coord)) for coord in valid_moves]
        next_coord = min(valid_move_costs, key=lambda x: x[1])[0] if valid_move_costs else None

        # Uh oh, we found no valid moves. Random move it is!
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
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
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
