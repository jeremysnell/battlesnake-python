from app.board import Board
from app.snake import Snake
from app.constants import *


class Context(object):
    def __init__(self, data, dna, traits):
        self.board = Board(data['board'])
        self.me = Snake(data['you'])

        # If no DNA is passed in, use the default values
        self.dna = dna.split('-') if dna else DEFAULT_DNA
        self.traits = traits.split('-')
