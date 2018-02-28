import random
import bottle
import os

from app.constants import OPPORTUNISTIC, MAX_OPPORTUNISTIC_EAT_COST, \
    AGGRESSIVE, GLUTTONOUS, INSECURE, DIRECTION_MAP, COOPERATIVE, HEAD_DANGER_COST
from app.pathfinder import PathFinder
from app.snake import PlayerSnake
from app.utility import point_to_coord, get_coord_neighbors, sub_coords


# TODO: Get response time down!!!
# TODO: Make snake head predictions for next turn? Could we be trapped? Untrapped?

# TODO: Weight based on relative size of flood fill areas?
# TODO: Add food distance calcs?
# TODO: Add trait ordering? (agg-glu is diff than glu-agg)
# TODO: If there's another, bigger head in a small space with you, BAD!
# TODO: Other's tails are very dangerous if they're about to eat
# TODO: Should being next to yourself always cost less?
# TODO: If our tail is in an area, it's safer
# TODO: Area danger based on fillable space, not total space
# TODO: Go after food we're closer to than any other snake first
# TODO: Cut off snakes, if nearby and aggressive
# TODO: Foresight when trapped


# Used by the /move endpoint to get the next move
def get_move(dna, traits):
    data = bottle.request.json

    # Get data about our snake
    me = PlayerSnake(data, dna, traits)

    # We'll use this for all pathing
    pathfinder = PathFinder(data, me)

    next_path = []

    # Find paths to all possible food, that we can reach in time
    food_paths = [path for path in pathfinder.get_paths_to_points(me.head, data['food']['data']) if len(path[1]) <= me.health]

    # Let's get the cheapest path to food
    best_food_path = min(food_paths, key=lambda x: x[0]) if food_paths else None

    # Eat if we're starving
    if best_food_path and me.is_starving:
        next_path = best_food_path

    # We're trapped, so let's pack in as tight as we can
    if pathfinder.is_trapped:
        fill_path = pathfinder.get_best_path_fill(me.head, me.length)
        if fill_path:
            # Format as a path
            next_path = (None, fill_path)

    # Eat food if it's close or we're peckish
    if best_food_path and ((me.has_trait(OPPORTUNISTIC) and best_food_path[0] <= me.dna(MAX_OPPORTUNISTIC_EAT_COST))
                           or (me.is_peckish and pathfinder.path_is_safe(best_food_path))):
        next_path = best_food_path

    # Try and get longer
    if not next_path and me.has_trait(GLUTTONOUS):

        # Are we the longest snake?
        im_longest = me.length > max([snake['length'] for snake in data['snakes']['data'] if snake['id'] != data['you']['id']])

        if best_food_path and not im_longest and pathfinder.path_is_safe(best_food_path):
            next_path = best_food_path

    # The bigger snakes eat the little ones
    # Path to a other snakes' head neighbor squares
    if not next_path and me.has_trait(AGGRESSIVE):
        # We'll use the name prefix to tell who's friendly
        friendly_snake_ids = [snake['id'] for snake in data['snakes']['data']
                              if snake['name'].split(' ')[0] == me.name.split(' ')[0]]
        enemy_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in data['snakes']['data']
                             if (not me.has_trait(COOPERATIVE) or snake['id'] not in friendly_snake_ids) and snake['id'] != data['you']['id']]
        enemy_snake_targets = [neighbor for head in enemy_snake_heads for neighbor in get_coord_neighbors(head)]
        attack_paths = pathfinder.get_paths_to_coords(me.head, enemy_snake_targets)
        best_attack_path = min(attack_paths, key=lambda x: x[0]) if attack_paths else None

        # Subtract one head danger from cost, since we're trying to path adjacent to a head
        if best_attack_path and pathfinder.path_is_safe(best_attack_path, me.dna(HEAD_DANGER_COST)):
            next_path = best_attack_path

    # Try and chase tail
    if not next_path and me.has_trait(INSECURE):
        tail_path = pathfinder.get_path_to_coord(me.head, me.tail)

        if tail_path and pathfinder.path_is_safe(tail_path):
            next_path = tail_path

    # Move to the safest adjacent square
    if not next_path:
        valid_move_costs = [(pathfinder.get_cost(me.head, coord), coord) for coord in pathfinder.valid_moves]

        if valid_move_costs:
            lowest_cost = min(valid_move_costs, key=lambda x: x[0])[0] if valid_move_costs else None
            next_coord = random.choice([move for cost, move in valid_move_costs if cost == lowest_cost])
        else:
            # Uh oh, we found no valid moves. Randomly move to our death!
            return {
                'move': random.choice(DIRECTION_MAP.values()),
                'taunt': 'Uh oh'
            }
    else:
        # Our target will be the second coord in the shortest path (the first coord is our current position)
        next_coord = next_path[1][1]

        print 'Name: %s - Next: %s - Target: %s - Cost: %s' % (me.name, next_path[1][0], next_path[1][-1], next_path[0])

    # Calculate to the change between our head and the next move
    coord_delta = sub_coords(next_coord, me.head)

    # Look up the name of the direction we're trying to move
    direction = DIRECTION_MAP[coord_delta]

    return {
        'move': direction,
        'taunt': direction
    }


#################
# API ENDPOINTS #
#################


@bottle.post('/move')
@bottle.post('/<traits>/move')
@bottle.post('/<dna>/<traits>/move')
@bottle.post('/<color>/<dna>/<traits>/move')
def move(dna='', traits='', color=''):
    return get_move(dna, traits)


@bottle.route('/')
@bottle.route('/<traits>/')
@bottle.route('/<dna>/<traits>/')
@bottle.route('/<color>/<dna>/<traits>/')
def static(dna='', traits='', color=''):
    return "the server is running"


@bottle.route('/static/<path:path>')
@bottle.route('/<traits>/static/<path:path>')
@bottle.route('/<dna>/<traits>/static/<path:path>')
@bottle.route('/<color>/<dna>/<traits>/static/<path:path>')
def static(path, dna='', traits='', color=''):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
@bottle.post('/<traits>/start')
@bottle.post('/<dna>/<traits>/start')
@bottle.post('/<color>/<dna>/<traits>/start')
def start(dna='', traits='', color=''):
    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    if color:
        color = "#" + color
    else:
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
        'taunt': '404 - Taunt not found',
        'head_url': head_url,
        'name': 'DNA Snake'
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
