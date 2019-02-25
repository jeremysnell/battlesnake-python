import os
import bottle

from app.api import *
from app.context import Context
from app.mover import Mover


@bottle.route('/')
def index():
    return '''
    Battlesnake documentation can be found at
       <a href="https://docs.battlesnake.io">https://docs.battlesnake.io</a>.
    '''


@bottle.route('/static/<path:path>')
def static(path):
    """
    Given a path, return the static file located relative
    to the static folder.

    This can be used to return the snake head URL in an API response.
    """
    return bottle.static_file(path, root='static/')


@bottle.post('/ping')
def ping():
    """
    A keep-alive endpoint used to prevent cloud application platforms,
    such as Heroku, from sleeping the application instance.
    """
    return ping_response()


@bottle.post('/start')
def start():
    color = "#00FF00"

    return start_response(color)


@bottle.post('/move')
@bottle.post('/<traits>/move')
@bottle.post('/<dna>/<traits>/move')
@bottle.post('/<color>/<dna>/<traits>/move')
def move(dna='', traits=''):
    data = bottle.request.json

    context = Context(data, dna, traits)
    mover = Mover(context)
    move_direction = mover.next_move()

    return move_response(move_direction)


@bottle.post('/end')
def end():
    return end_response()


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()


if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '192.168.98.15'),
        # host=os.getenv('IP', '192.168.0.19'),
        port=os.getenv('PORT', '8080'),
        debug=True)
