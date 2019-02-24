import random

from app.constants import *
from app.pathfinder import PathFinder
from app.utility import get_coord_neighbors, sub_coords


class Mover(object):
    next_path = []

    _best_path_to_food = []
    _best_path_to_my_tail = []

    def __init__(self, context):
        self.context = context
        self.pathfinder = PathFinder(context)

    def next_move(self):
        # Eat if we're starving
        if self.context.me.health < self.context.dna[STARVING_THRESHOLD]:
            self.next_path = self.best_path_to_food()

        # We're trapped, we better switch up our approach
        if self.pathfinder.is_trapped:
            # Try and follow our tail to get out
            self.next_path = self.best_path_to_my_tail()

            if not self.next_path:
                self.next_path = self._get_path_to_my_body_segment_closest_to_tail()

            if not self.next_path:
                self.next_path = self._get_best_path_to_any_tail()

        # Eat if opportunistic or peckish
        if not self.next_path and (OPPORTUNISTIC in self.context.traits or
                                   self.context.me.health < self.context.dna[PECKISH_THRESHOLD]):
            if self.best_path_to_food() and (
                    self.best_path_to_food()[0] <= self.context.dna[MAX_OPPORTUNISTIC_EAT_COST] or
                    self.pathfinder.path_is_safe(self.best_path_to_food())):
                self.next_path = self.best_path_to_food()

        # Try and get longer
        if not self.next_path and GLUTTONOUS in self.context.traits and \
                not self.context.board.is_longest_snake(self.context.me):
            if self.best_path_to_food() and self.pathfinder.path_is_safe(self.best_path_to_food()):
                self.next_path = self.best_path_to_food()

        # The big snakes eat the little ones
        if not self.next_path and AGGRESSIVE in self.context.traits:
            self.next_path = self._get_best_attack_path()

        # Try and chase tail
        if not self.next_path and INSECURE in self.context.traits:
            self.next_path = self.best_path_to_my_tail()

        # Next move is second coord in path (the first coord is our current position)
        next_coord = self.next_path[1][1] if self.next_path else None

        # Move to the safest adjacent square
        if not next_coord:
            next_coord = random.choice(self._get_safest_moves())

        # Calculate to the change between our head and the next move
        coord_delta = sub_coords(next_coord, self.context.me.head) if next_coord else None

        # Look up the name of the direction we're trying to move, or move randomly, if we're going to die
        direction = DIRECTION_MAP[coord_delta] if coord_delta else random.choice(list(DIRECTION_MAP.values()))

        return direction

    def best_path_to_food(self):
        if not self._best_path_to_food:
            self._best_path_to_food = self.pathfinder.get_best_path_to_coords(self.context.me.head,
                                                                              self.context.board.food,
                                                                              self.context.me.health)
        return self._best_path_to_food

    def best_path_to_my_tail(self):
        if not self._best_path_to_my_tail:
            self._best_path_to_my_tail = self.pathfinder.get_best_path_to_coords(self.context.me.head,
                                                                                 [self.context.me.tail],
                                                                                 self.context.me.health)
        return self._best_path_to_my_tail

    def _get_path_to_my_body_segment_closest_to_tail(self):
        # Try and path to the segment of our body closest to our tail,
        # as long as we have enough room to get there
        for index, coord in enumerate(reversed(self.context.me.body)):
            body_paths = self.pathfinder.get_paths_to_coords(self.context.me.head, get_coord_neighbors(coord))
            valid_body_paths = [path for path in body_paths if len(path[1]) >= index + 1]

            # We found a way out! Probably...
            return min(valid_body_paths, key=lambda x: x[0]) if valid_body_paths else None

    def _get_best_path_to_any_tail(self):
        # TODO: Should it be closest tail?
        # Ok, let's try and follow any tail we can find
        other_tails = [snake.tail for snake in self.context.board.snakes
                       if snake.id != self.context.me.id]
        other_tail_neighbors = [neighbor for tail in other_tails for neighbor in get_coord_neighbors(tail)]

        return self.pathfinder.get_best_path_to_coords(self.context.me.head,
                                                       other_tail_neighbors,
                                                       self.context.me.health)

    def _get_best_attack_path(self):
        friendly_snakes = [snake for snake in self.context.board.snakes if snake.name == self.context.me.name]
        enemy_snake_heads = [snake.head for snake in self.context.board.snakes
                             if snake not in friendly_snakes]
        enemy_snake_targets = [neighbor for head in enemy_snake_heads for neighbor in get_coord_neighbors(head)]

        return self.pathfinder.get_best_path_to_coords(self.context.me.head,
                                                       enemy_snake_targets,
                                                       self.context.me.health)

        # Subtract one head danger from cost, since we're trying to path adjacent to a head
        # if best_attack_path and pathfinder.path_is_safe(best_attack_path, me.dna(HEAD_DANGER_COST)):
        #   next_path = best_attack_path

    def _get_safest_moves(self):
        valid_moves_and_costs = [(self.pathfinder.get_cost(self.context.me.head, coord), coord)
                                 for coord in self.pathfinder.valid_moves]

        if valid_moves_and_costs:
            lowest_cost = min(valid_moves_and_costs, key=lambda x: x[0])[0]
            return [move for cost, move in valid_moves_and_costs if cost == lowest_cost]

        return [None]
