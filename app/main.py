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
    return finder(head_coord, target_coord)


# Returns the shortest paths to each point, using the astar algorithm
def get_paths_to_points(finder, head_coord, target_points):
    return [path for path in [finder(head_coord, coord) for coord in [point_to_coord(point) for point in target_points]] if path[0]]


# Get the four neighbouring squares for a given coord (up, down, left, right)
def get_coord_neighbours(coord):
    return [add_coords(coord, dir_coord) for dir_coord in DIRECTION_MAP.keys()]


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


def get_valid_neighbours(coord, map_size, fatal_coords):

    # TODO: Don't go into a space smaller than your body, using flood fill

    # Possible neighbours of input coords
    coord_neighbors = get_coord_neighbours(coord)

    valid_neighbours = [
        neighbor for neighbor in coord_neighbors
        if 0 <= neighbor[0] < map_size[0]       # X Coord must be within map
        and 0 <= neighbor[1] < map_size[1]      # Y Coord must be within map
        and neighbor not in fatal_coords        # Don't crash into any snake
    ]

    return valid_neighbours


# Node cost calculations used to weight safer or "better" paths
def get_cost(coord1, coord2, map_size, you_head, you_tail, danger_coords):
    # Cost is weighted towards squares in the center, since these are safer(?)
    # cost = (abs(coord2[0] - map_size[0] / 2) + abs(coord2[1] - map_size[1] / 2)) * 2
    cost = 1

    # Pathing near walls costs more
    if coord2[0] == 0 or coord2[0] == map_size[0] - 1:
        cost += 5
    if coord2[1] == 0 or coord2[1] == map_size[1] - 1:
        cost += 5

    # Pathing into dangerous coords costs much more
    if coord2 in danger_coords:
        cost += 50

    # Actually moving into our tail should be strongly discouraged!
    if coord1 == you_head and coord2 == you_tail:
        cost = 1000

    return cost


@bottle.post('/move')
def move():
    data = bottle.request.json

    # Our snake's data
    you_coords = [point_to_coord(point) for point in data['you']['body']['data']]
    you_head = you_coords[0]
    you_tail = you_coords[-1]
    you_health = data['you']['health']
    you_length = data['you']['length']

    # Avoid squares that will kill us
    snake_coords = [point_to_coord(point) for snake in data['snakes']['data'] for point in snake['body']['data']]
    fatal_coords = [coord for coord in snake_coords if coord != you_tail]

    # Avoid squares adjacent to enemy snake tails, since they're dangerous
    other_snake_tails = [point_to_coord(snake['body']['data'][-1]) for snake in data['snakes']['data'] if snake['id'] != data['you']['id']]
    danger_coords = [neighbour for head in other_snake_tails for neighbour in get_coord_neighbours(head)]

    # Avoid squares adjacent to enemy snake heads, since they're dangerous
    other_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data'] if snake['id'] != data['you']['id']]
    danger_coords += [neighbour for head in other_snake_heads for neighbour in get_coord_neighbours(head)]

    map_size = (data['width'], data['height'])

    # Used by the astar algorithm to evaluate path nodes
    def neighbors_func(node):
        return get_valid_neighbours(node, map_size, fatal_coords)

    # Used by the astar algorithm to evaluate node costs
    def cost_func(node1, node2):
        return get_cost(node1, node2, map_size, you_head, you_tail, danger_coords)

    # Create the astar path finder
    finder = astar.pathfinder(neighbors=neighbors_func, cost=cost_func)

    next_path = []

    # TODO: Maybe we want to eat as much as possible until we reach a certain length?
    # TODO: Once we're bigger than other snakes, go for their heads?
    # TODO: Use node weighting to simplify ifs

    # Who's the longest snake? Could be useful...
    # longest = max([snake['length'] for snake in data['snakes']['data'] if snake['id'] != data['you']['id']] or [None])

    # Find paths to all possible food
    food_paths = get_paths_to_points(finder, you_head, data['food']['data'])

    # Let's follow the cheapest path, as long as we can get there before dying
    best_food_path = min([path for path in food_paths if len(path[1]) <= you_health], key=lambda x: x[0]) if food_paths else None

    # Opportunistically eat close food
    if best_food_path and best_food_path[0] <= 2:
        next_path = best_food_path

    # If snake is hungry, then try and eat some food
    if not next_path and you_health < 50:
        next_path = best_food_path

        # No luck. We're hungry, so try again, ignoring danger
        if not next_path:
            danger_coords = []
            paths = get_paths_to_points(finder, you_head, data['food']['data'])
            next_path = min([path for path in paths if path[0] <= you_health], key=lambda x: x[0]) if paths else None

    # If we're not going after food, or can't find a path to any, just follow our tail
    if not next_path:
        # Find path to our tail
        next_path = get_path_to_coord(finder, you_head, you_tail)

    # Can't get to our tail safely, things aren't looking good!
    # Move to any safe adjacent square, if possible
    if not next_path:
        valid_moves = neighbors_func(you_head)
        next_coord = random.choice(valid_moves) if valid_moves else None

        if not next_coord:
            # Uh oh, we found no valid moves. Random move it is!
            return {
                'move': random.choice(DIRECTION_MAP.values()),
                'taunt': 'Uh oh'
            }
    else:
        # Get the second coord in the shortest path (the first coord is our current position)
        next_coord = next_path[1][1]

        print 'Target: %s - Cost: %s' % (next_path[1][-1], next_path[0])

    # Calculate to the change between our head and the next move
    coord_delta = sub_coords(next_coord, you_head)

    # Look up the name of the direction we're trying to move
    direction = DIRECTION_MAP[coord_delta]

    return {
        'move': direction,
        'taunt': direction
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '10.4.19.137'),
        port=os.getenv('PORT', '8080'),
        debug = True)
