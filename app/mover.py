import random
from copy import deepcopy

from app.constants import *
from app.pathfinder import PathFinder
from app.utility import get_coord_neighbors, sub_coords


class Mover(object):
    def __init__(self, context):
        self.context = context
        self.pathfinder = PathFinder(context)

        self._best_path_to_food = []
        self._best_path_to_my_tail = []

    def next_move(self):
        next_path = []
        motivation = ""

        # We're trapped, we need to find a new approach
        if self.pathfinder.is_trapped():
            motivation = "Is Trapped"
            # Try and follow our tail to get out
            next_path = self.best_path_to_my_tail()

            # Ok, try and find a way to the square closest to our tail
            if not next_path:
                next_path = self._get_path_to_body_segment_closest_to_tail([self.context.me])

            # Ok, anyone's closest tail square will do
            if not next_path:
                next_path = self._get_path_to_body_segment_closest_to_tail(self.context.enemy_snakes())

        # Eat if we're starving
        if self.context.me.health < self.context.dna[STARVING_THRESHOLD]:
            motivation = "Starving"
            next_path = self.best_path_to_food()
        # Eat if opportunistic or peckish
        elif OPPORTUNISTIC in self.context.traits or self.context.me.health < self.context.dna[PECKISH_THRESHOLD]:
            motivation = "Opportunistic or Peckish"
            # Are we adjacent to the food?
            # Will eating the food put us in a smaller space?
            if self.best_path_to_food() and len(self.best_path_to_food()[1]) <= 2:
                # and (not next_path or self.best_path_to_food()[0] <= next_path[0]):
                move = self.best_path_to_food()[1][1]
                move_pathfinder = self._get_pathfinder_for_move(move)

                # Will we still be able to get where we were going?
                if not next_path or move_pathfinder.get_path_to_coord(move, next_path[1][-1]):
                    # self.best_path_to_food()[0] <= self.context.dna[MAX_OPPORTUNISTIC_EAT_COST] or
                    # self.pathfinder.path_is_safe(self.best_path_to_food())
                    next_path = self.best_path_to_food()

        # Try and get longer
        if not next_path and GLUTTONOUS in self.context.traits and \
                not self.context.board.is_longest_snake(self.context.me):
            motivation = "Gluttonous"
            if self.best_path_to_food() and self.pathfinder.path_is_safe(self.best_path_to_food()):
                next_path = self.best_path_to_food()

        # The big snakes eat the little ones
        if not next_path and AGGRESSIVE in self.context.traits:
            motivation = "Aggressive"
            next_path = self._get_best_attack_path()

        # Try and chase tail
        if not next_path and INSECURE in self.context.traits:
            motivation = "Insecure"
            next_path = self.best_path_to_my_tail()

        # Next move is second coord in path (the first coord is our current position)
        next_coord = next_path[1][1] if next_path else None

        # Move to the safest adjacent square
        if not next_coord:
            motivation = "Random"
            next_coord = random.choice(self._get_safest_moves())

        # Calculate to the change between our head and the next move
        coord_delta = sub_coords(next_coord, self.context.me.head) if next_coord else None

        # Look up the name of the direction we're trying to move, or move randomly, if we're going to die
        direction = DIRECTION_MAP[coord_delta] if coord_delta else random.choice(list(DIRECTION_MAP.values()))

        print("%s is moving %s because it is %s (Game %s - Turn %s)" % (self.context.me.name, direction, motivation,
                                                                        self.context.game_id, self.context.turn))

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

    def _get_path_to_body_segment_closest_to_tail(self, snakes):
        # Try and path to the segment of the snake's body closest to the tail,
        # as long as the tail will be there when we arrive
        for snake in snakes:
            for index, coord in enumerate(reversed(snake.body)):
                body_paths = self.pathfinder.get_paths_to_coords(self.context.me.head, get_coord_neighbors(coord))
                valid_body_paths = [path for path in body_paths if len(path[1]) >= index + 1]

                # We found a way out! Probably...
                if valid_body_paths:
                    return min(valid_body_paths, key=lambda x: x[0])

        return None

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
        smaller_snake_heads = [snake.head for snake in self.context.board.snakes
                               if snake.name != self.context.me.name and snake.length < self.context.me.length]

        pathfinder_without_fatal_heads = deepcopy(self.pathfinder)
        pathfinder_without_fatal_heads.remove_fatal_coords(smaller_snake_heads)

        return pathfinder_without_fatal_heads.get_best_path_to_coords(self.context.me.head,
                                                                      smaller_snake_heads,
                                                                      self.context.me.health)

    def _get_safest_moves(self):
        valid_moves_and_costs = [(self.pathfinder.get_cost(self.context.me.head, coord), coord)
                                 for coord in self.pathfinder.valid_moves()]

        if valid_moves_and_costs:
            lowest_cost = min(valid_moves_and_costs, key=lambda x: x[0])[0]
            return [move for cost, move in valid_moves_and_costs if cost == lowest_cost]

        return [None]

    def _get_pathfinder_for_move(self, coord):
        future_context = deepcopy(self.context)

        is_food = coord in future_context.board.food

        if is_food:
            future_context.board.food.remove(coord)

        future_context.me.moved(coord, is_food)

        return PathFinder(future_context)
