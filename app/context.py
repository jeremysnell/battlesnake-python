from app.board import Board
from app.snake import Snake
from app.constants import *


class Context(object):
    def __init__(self, data, dna, traits):
        self.game_id = data['game']['id']
        self.turn = data['turn']

        self.board = Board(data['board'])
        self.me = Snake(data['you'])

        # If no DNA is passed in, use the default values
        self.dna = [int(dna or DEFAULT_DNA[i]) for i, dna in enumerate(dna.split('-'))] if dna else DEFAULT_DNA
        self.traits = traits.split('-')

    def enemy_snakes(self):
        return [snake for snake in self.board.snakes if snake.id != self.me.id]
