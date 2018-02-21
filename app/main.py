import bottle
import os
import random
from pypaths import astar


@bottle.route('/')
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
    data = bottle.request.json
    game_id = data.get('game_id')
    board_width = data.get('width')
    board_height = data.get('height')

    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    # TODO: Do things with data

    return {
        'color': '#00FF00',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url
    }


def get_valid_next_move(coord, data):
    direction_map = {
        'UP': (0, -1),
        'RIGHT': (1, 0),
        'DOWN': (0, 1),
        'LEFT': (-1, 0)
    }

    snake_coords = [(point['x'], point['y']) for snake in data['snakes']['data'] for point in snake['body']['data']]

    # TODO: Add other snakes' head border squares as danger zones
    # TODO: Snake can still die if it's too close to its tail when it eats a food
    # TODO: Tails border squares should be danger zones too
    # TODO: Don't go into a space smaller than your body

    next_up = tuple(map(sum, zip(coord, direction_map['UP'])))
    next_down = tuple(map(sum, zip(coord, direction_map['DOWN'])))
    next_left = tuple(map(sum, zip(coord, direction_map['LEFT'])))
    next_right = tuple(map(sum, zip(coord, direction_map['RIGHT'])))

    valid_moves = []

    if all(coord != next_up for coord in snake_coords) and next_up[1] >= 0:
        valid_moves.append(next_up)
    if all(coord != next_down for coord in snake_coords) and next_down[1] < data['height']:
        valid_moves.append(next_down)
    if all(coord != next_left for coord in snake_coords) and next_left[0] >= 0:
        valid_moves.append(next_left)
    if all(coord != next_right for coord in snake_coords) and next_right[0] < data['width']:
        valid_moves.append(next_right)

    return valid_moves


def add_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x + y, coord_one, coord_two))


def sub_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x - y, coord_one, coord_two))


def point_to_coord(point):
    return point['x'], point['y']


def get_paths_to_coords(finder, head_coords, target_coords):
    return [path for path in [finder(head_coords, coord) for coord in target_coords] if path[0]]


def get_paths_to_points(finder, head_coords, target_points):
    return get_paths_to_coords(finder, head_coords, [point_to_coord(point) for point in target_points])


@bottle.post('/move')
def move():
    data = bottle.request.json

    direction_map = {
        (0, -1): 'up',
        (0, 1): 'down',
        (-1, 0): 'left',
        (1, 0): 'right'
    }

    def get_neighbors(node):
        return get_valid_next_move(node, data)

    finder = astar.pathfinder(neighbors=get_neighbors)

    you_coords = [point_to_coord(point) for point in data['you']['body']['data']]

    head_coords = you_coords[0]

    paths = []

    # Snake is hungry! Or we're unpacking at the beginning of the game.
    if data['you']['health'] < 30 or data['turn'] < data['you']['length']:
        paths = get_paths_to_points(finder, head_coords, data['food']['data'])

    if not paths:
        tail_neighbour_coords = [add_coords(you_coords[-1], coord) for coord in direction_map.keys()]
        paths = get_paths_to_coords(finder, head_coords, tail_neighbour_coords)

    if not paths:
        raise Exception

    path = min(paths, key=lambda x: x[0])

    next_coords = path[1][1]

    coord_delta = sub_coords(next_coords, head_coords)

    direction = direction_map[coord_delta]

    print direction
    return {
        'move': direction,
        'taunt': 'battlesnake-python!'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '10.4.19.137'),
        port=os.getenv('PORT', '8080'),
        debug = True)
