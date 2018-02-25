import random
import bottle
import os

from app.constants import TRAIT_OPPORTUNISTIC, MAX_OPPORTUNISTIC_EAT_COST, PECKISH_THRESHOLD, MAX_COST_CONSIDERED_SAFE, \
    STARVING_THRESHOLD, TRAIT_AGGRESSIVE, TRAIT_GLUTTONOUS, TRAIT_INSECURE, DIRECTION_MAP
from app.pathfinder import PathFinder
from app.utility import point_to_coord, get_coord_neighbors, sub_coords


@bottle.post('/move')
@bottle.post('/<traits>/move')
def move(traits=''):
    # TODO: Weight based on relative size of flood fill areas?
    # TODO: Weight so open space is better than corridors?
    # TODO: Make snake head predictions for next turn? Could we be trapped? Untrapped?
    # TODO: Add food distance calcs?
    # TODO: Add trait ordering? (agg-glu is diff than glu-agg)
    # TODO: Get DNA working
    # TODO: If there's another, bigger head in a small space with you, BAD!
    # TODO: Tail is very dangerous if about to eat
    # TODO: Should being next to yourself always cost less?
    # TODO: Better space packing?

    data = bottle.request.json

    # Snake behavior controls
    snake_traits = traits.split('-')

    # TODO: Dict?
    # Our snake's data
    my_length = data['you']['length']
    my_health = data['you']['health']
    my_coords = [point_to_coord(point) for point in data['you']['body']['data']]
    my_head = my_coords[0]
    my_tail = my_coords[-1]

    pathfinder = PathFinder(data, snake_traits, my_coords, my_head, my_length)

    next_path = []

    # Find paths to all possible food, that we can reach in time
    food_paths = [path for path in pathfinder.get_paths_to_points(my_head, data['food']['data']) if len(path[1]) <= my_health]

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
        attack_paths = pathfinder.get_paths_to_coords(my_head, smaller_snake_targets)
        best_attack_path = min(attack_paths, key=lambda x: x[0]) if attack_paths else None

        if best_attack_path and best_attack_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = best_attack_path

    # Try and get longer
    if not next_path and TRAIT_GLUTTONOUS in snake_traits:

        # Are we the longest snake?
        im_longest = my_length > max([snake['length'] for snake in data['snakes']['data'] if snake['id'] != data['you']['id']])

        if best_food_path and not im_longest and best_food_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = best_food_path

    # Try and chase tail
    if not next_path and TRAIT_INSECURE in snake_traits:
        tail_path = pathfinder.get_path_to_coord(my_head, my_tail)

        if tail_path and tail_path[0] < MAX_COST_CONSIDERED_SAFE:
            next_path = tail_path

    # Move to the safest adjacent square
    if not next_path:
        valid_move_costs = [(pathfinder.get_cost(my_head, coord), coord) for coord in pathfinder.valid_moves]
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
