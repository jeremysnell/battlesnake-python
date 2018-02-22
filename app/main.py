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


# Returns the shortest paths to each coord, using the astar algorithm
def get_paths_to_coords(finder, head_coord, target_coords):
    return [path for path in [finder(head_coord, coord) for coord in target_coords] if path[0]]


# Returns the shortest paths to each point, using the astar algorithm
def get_paths_to_points(finder, head_coords, target_points):
    return get_paths_to_coords(finder, head_coords, [point_to_coord(point) for point in target_points])


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


def get_valid_neighbours(coord, data, ignore_head_danger):

    # TODO: Other snake tails border squares can be danger zones too, if they eat food
    # TODO: Don't go into a space smaller than your body, using flood fill

    # Coords of all snakes' bodies, including heads
    snakes_coords = [point_to_coord(point) for snake in data['snakes']['data'] for point in snake['body']['data']]

    # Coords of all enemy snakes' heads
    other_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data'] if snake['id'] != data['you']['id']]

    # Coords of all squares adjacent to an enemy snake's head. We avoid these squares, since they are dangerous
    other_head_neighbors = [neighbour for head in other_snake_heads for neighbour in get_coord_neighbours(head)]

    # Possible neighbours of input coords
    coord_neighbors = get_coord_neighbours(coord)

    valid_neighbours = [
        neighbor for neighbor in coord_neighbors
        if 0 <= neighbor[0] < data['width']         # X Coord must be within map
        and 0 <= neighbor[1] < data['height']       # Y Coord must be within map
        and neighbor not in snakes_coords           # Don't crash into any snake
        and (neighbor not in other_head_neighbors   # Avoid dangerous squares next to other snakes' heads
             or ignore_head_danger)                 # ...unless we're ignoring the danger
    ]

    return valid_neighbours


@bottle.post('/move')
def move():
    data = bottle.request.json

    # Used to control whether we avoid coords adjacent to snake heads when pathing
    # If things are getting desperate, we'll ignore the danger
    ignore_head_danger = False

    # Used by the astar algorithm to evaluate path nodes
    def get_neighbors(node):
        return get_valid_neighbours(node, data, ignore_head_danger)

    # Create the astar path finder
    finder = astar.pathfinder(neighbors=get_neighbors)

    # Our snake's body coords
    you_coords = [point_to_coord(point) for point in data['you']['body']['data']]

    # Our current head coord
    you_head = you_coords[0]

    paths = []

    # TODO: Maybe we want to eat as much as possible until we reach a certain length?
    # TODO: Once we're bigger than other snakes, go for their heads?
    # TODO: Maybe eat food that is opportunistically close?
    # TODO: Add path weighting, based on snake/food/wall proximity?

    longest = max([snake['length'] for snake in data['snakes']['data'] if snake['id'] != data['you']['id']])

    # If snake is hungry, or we're "uncoiling", or we're not the longest snake, then try and eat some food
    if data['you']['health'] < 30 or data['turn'] < data['you']['length'] or data['you']['length'] <= longest:
        # Find paths to all possible food
        paths = get_paths_to_points(finder, you_head, data['food']['data'])

    # If we're not going after food, or can't find a path to any, just follow our tail
    if not paths:
        # It's dangerous to follow our actual tail coord, so let's follow one of our tail neighbour coords instead
        tail_neighbour_coords = get_coord_neighbours(you_coords[-1])

        # If our head is already next to our tail, we should remove that neighbour from possible targets
        valid_neighbour_coords = [coord for coord in tail_neighbour_coords if coord != you_head]

        # Find paths to our valid tail neighbours
        paths = get_paths_to_coords(finder, you_head, valid_neighbour_coords)

    # Can't get to food or our tail, things aren't looking good!
    # Move to any safe adjacent square, if possible
    if not paths:
        head_neighbour_coords = get_coord_neighbours(you_head)
        paths = get_paths_to_coords(finder, you_head, head_neighbour_coords)

    # Try again, ignoring head danger
    if not paths:
        ignore_head_danger = True
        head_neighbour_coords = get_coord_neighbours(you_head)
        paths = get_paths_to_coords(finder, you_head, head_neighbour_coords)

    # Uh oh, we found no valid path. Random move it is!
    if not paths:
        return {
            'move': random.choice(DIRECTION_MAP.values()),
            'taunt': 'Uh oh'
        }

    # Let's follow the shortest path of the paths we found
    path = min(paths, key=lambda x: x[0])

    # Get the second coord in the shortest path (the first coord is our current position)
    next_coord = path[1][1]

    # Calculate to the change between our head and the next move
    coord_delta = sub_coords(next_coord, you_head)

    # Look up the name of the direction we're trying to move
    direction = DIRECTION_MAP[coord_delta]

    return {
        'move': direction,
        'taunt': 'DROP TABLE snakes;'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '10.4.19.137'),
        port=os.getenv('PORT', '8080'),
        debug = True)
