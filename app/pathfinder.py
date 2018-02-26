from pypaths import astar

from app.constants import BASE_COST, TRAPPED_BODY_ADJACENT_COST, WALL_DANGER_COST, HEAD_DANGER_COST, TRAP_DANGER_COST, \
    TRAPPED_WALL_ADJACENT_COST, TRAP_SIZE_MULTIPLIER, TRAIT_FORESIGHTED, BODY_DANGER_COST
from app.utility import point_to_coord, get_coord_neighbors, get_absolute_distance, is_adjacent_to_coords, \
    get_adjacent_coords


class PathFinder:
    def __init__(self, data, snake_traits, my_coords, my_head, my_length):
        self.data = data
        self.snake_traits = snake_traits
        self.my_coords = my_coords
        self.my_head = my_head
        self.my_length = my_length
        self.my_id = data['you']['id']
        self.my_body = my_coords[1:-1] if my_length > 2 else []
        self.map_size = (data['width'], data['height'])

        self.fatal_coords = self._get_fatal_coords()

        # Avoid squares adjacent to enemy snake heads, since they're dangerous
        # Unless we're longer than them, then we're safe
        self.bigger_snake_heads = [point_to_coord(snake['body']['data'][0]) for snake in self.data['snakes']['data'] if
                                   snake['id'] != self.my_id and snake['length'] >= self.my_length]
        self.head_danger_coords = [neighbor for head in self.bigger_snake_heads for neighbor in
                                   get_coord_neighbors(head)]

        # Get valid moves
        self.valid_moves = self.get_valid_neighbors(self.my_head)

        # Find the size of the area we'd be moving into, for each valid move
        self.fill_coords = dict(
            [(move_coord, self.flood_fill(move_coord, self.my_length * TRAP_SIZE_MULTIPLIER)) for move_coord in
             self.valid_moves])

        # If the area is smaller than our size (with multiplier), it's dangerous
        self.coord_to_trap_danger = dict(
            [(coord, len(fill)) for coord, fill in self.fill_coords.items() if fill])

        # We're enclosed in an area smaller than our body
        self.im_trapped = len(self.coord_to_trap_danger) == len(self.fill_coords)

        self._finder = self._get_astar_pathfinder()

    # Determines the size of the safe area around a coord
    def flood_fill(self, start_coord, max_fill_size=None):
        explored = []
        queue = [start_coord]
        while queue:
            next_coord = queue.pop(0)
            explored.append(next_coord)

            if max_fill_size and len(explored) == max_fill_size:
                return None

            neighbors = self.get_valid_neighbors(next_coord)
            for neighbor in neighbors:
                if neighbor not in queue and neighbor not in explored:
                    queue.append(neighbor)

        return explored

    # Finds the best path to fill an area
    def best_path_fill(self, start_coord, max_path_length=None):
        def recurse_path(coord, path):
            current_path = list(path)
            current_path.append(coord)
            neighbors = [neighbor for neighbor in self.get_valid_neighbors(coord) if neighbor not in current_path]
            if neighbors and (not max_path_length or len(current_path) < max_path_length):
                return max([recurse_path(neighbor, current_path) for neighbor in neighbors], key=lambda x: len(x))
            return current_path

        return recurse_path(start_coord, [])

    def _get_fatal_coords(self):
        # Avoid squares that will kill us
        snake_bodies = [[point_to_coord(point) for point in snake['body']['data']]
                        for snake in self.data['snakes']['data']]

        # Don't move into any coords where a snake body is,
        # unless we're far enough away that it won't be there when we get there
        fatal_coords = [coord for snake_body in snake_bodies for coord in snake_body
                        if TRAIT_FORESIGHTED not in self.snake_traits
                        or len(snake_body) - (snake_body.index(coord) + 1) >=
                        min(get_absolute_distance(self.my_head, coord), len(snake_body))]

        return fatal_coords

    # Node cost calculation, which will make more dangerous paths cost more
    def get_cost(self, node1, node2):
        cost = BASE_COST

        # Pathing near walls costs more, unless we're trapped, then it's actually better
        if node2[0] == 0 or node2[0] == self.map_size[0] - 1:
            cost += TRAPPED_WALL_ADJACENT_COST if self.im_trapped else WALL_DANGER_COST
        if node2[1] == 0 or node2[1] == self.map_size[1] - 1:
            cost += TRAPPED_WALL_ADJACENT_COST if self.im_trapped else WALL_DANGER_COST

        # Pathing near other snake's bodies is more expensive, unless we're trapped
        cost += len(get_adjacent_coords(node2, self.fatal_coords)) * (TRAPPED_BODY_ADJACENT_COST if self.im_trapped else BODY_DANGER_COST)

        # Pathing into squares adjacent to a bigger snake head costs much more
        if node2 in self.head_danger_coords:
            cost += HEAD_DANGER_COST

        # Pathing into a small area costs more, based on how small it is compared to our length
        # If we're already trapped, and no moves make us "more" trapped, ignore the danger
        if (not self.im_trapped or len(set(self.coord_to_trap_danger.values())) > 1) \
                and node2 in self.coord_to_trap_danger.keys():
            cost += (1 - (self.coord_to_trap_danger[node2] / float(self.my_length * TRAP_SIZE_MULTIPLIER))) * TRAP_DANGER_COST

        return max(cost, 1)

    # Find non-fatal node neighbors
    def get_valid_neighbors(self, coord):
        # Possible neighbors of input coords
        coord_neighbors = get_coord_neighbors(coord)

        valid_neighbors = [
            neighbor for neighbor in coord_neighbors
            if 0 <= neighbor[0] < self.map_size[0]  # X Coord must be within map
               and 0 <= neighbor[1] < self.map_size[1]  # Y Coord must be within map
               and (neighbor not in self.fatal_coords)  # Don't crash into any snake
        ]

        return valid_neighbors

    def _get_astar_pathfinder(self):
        # Used by the astar algorithm to evaluate node costs
        def cost_func(node1, node2):
            return self.get_cost(node1, node2)

        # Used by the astar algorithm to evaluate path nodes
        def neighbors_func(node):
            return self.get_valid_neighbors(node)

        # Create the astar path finder
        return astar.pathfinder(neighbors=neighbors_func, cost=cost_func)

    # Returns the cheapest path to a coord, using the astar algorithm
    def get_path_to_coord(self, source_coord, target_coord):
        path = self._finder(source_coord, target_coord)
        return path if path[0] else None

    # Returns the shortest paths to each point, using the astar algorithm
    def get_paths_to_coords(self, source_coord, target_coords):
        return [path for path in [self.get_path_to_coord(source_coord, coord) for coord in target_coords] if path]

    # Returns the shortest paths to each point, using the astar algorithm
    def get_paths_to_points(self, source_coord, target_points):
        return self.get_paths_to_coords(source_coord, [point_to_coord(point) for point in target_points])