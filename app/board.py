from app.snake import Snake
from app.utility import point_to_coord


class Board(object):
    def __init__(self, data):
        self.height = data['height']
        self.width = data['width']
        self.food = [point_to_coord(point) for point in data['food']]
        self.snakes = [Snake(snake) for snake in data['snakes']]
        self.longest_snake = max([snake.length for snake in self.snakes])

    def is_longest_snake(self, snake):
        return max([snake.id for snake in self.snakes]) == snake.id
