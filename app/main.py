import random

import bottle
import os
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

    s4_colors = {
        'indigo': '#4E54A4',
        'green': '#44B5AD',
        'orange': '#F37970',
        'purple': '#AA66AA'
    }

    # snake_name = data['you']['name']
    # color = next((hexval for color, hexval in colors.items() if color in snake_name), colors['GREEN'])

    color = random.choice(s4_colors.values())

    print color

    return {
        'color': color,
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url
    }


DIRECTION_MAP = {
    (0, -1): 'up',
    (0, 1): 'down',
    (-1, 0): 'left',
    (1, 0): 'right'
}


def get_valid_neighbours(coord, data):

    # TODO: Other snake tails border squares should be danger zones too, if they eat food
    # TODO: Don't go into a space smaller than your body
    # TODO: Ignore rules if stuck

    snake_coords = [(point['x'], point['y']) for snake in data['snakes']['data'] for point in snake['body']['data']]
    other_snake_heads = [(snake['body']['data'][0]['x'], snake['body']['data'][0]['y']) for snake in data['snakes']['data'] if snake['id'] != data['you']['id']]
    other_head_neighbors = [add_coords(head, dir_coord) for dir_coord in DIRECTION_MAP.keys() for head in other_snake_heads]
    all_neighbors = [add_coords(coord, dir_coord) for dir_coord in DIRECTION_MAP.keys()]

    valid_neighbours = [coord for coord in all_neighbors
                        if 0 <= coord[0] < data['width']
                        and 0 <= coord[1] < data['height']
                        and coord not in snake_coords
                        and coord not in other_head_neighbors]

    return valid_neighbours


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

    def get_neighbors(node):
        return get_valid_neighbours(node, data)

    finder = astar.pathfinder(neighbors=get_neighbors)

    you_coords = [point_to_coord(point) for point in data['you']['body']['data']]

    head_coords = you_coords[0]

    paths = []

    # TODO: Maybe we want to eat as much as possible until we reach a certain length?
    # TODO: Maybe eat food that is opportunistically close?

    # Snake is hungry! Or we're unpacking at the beginning of the game.
    if data['you']['health'] < 30 or data['turn'] < data['you']['length']:
        paths = get_paths_to_points(finder, head_coords, data['food']['data'])

    if not paths:
        tail_neighbour_coords = [add_coords(you_coords[-1], coord) for coord in DIRECTION_MAP.keys()]
        paths = get_paths_to_coords(finder, head_coords, tail_neighbour_coords)

    if not paths:
        raise Exception

    path = min(paths, key=lambda x: x[0])

    next_coords = path[1][1]

    coord_delta = sub_coords(next_coords, head_coords)

    direction = DIRECTION_MAP[coord_delta]

    print direction
    return {
        'move': direction,
        'taunt': 'DROP TABLE snakes;'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '192.168.0.19'),
        port=os.getenv('PORT', '8080'),
        debug = True)
