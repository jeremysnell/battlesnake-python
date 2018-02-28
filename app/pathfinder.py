from pypaths import astar

from app.constants import BASE_COST, WALL_DANGER_COST, HEAD_DANGER_COST, TRAP_DANGER_COST, \
    FORESIGHTED, BODY_DANGER_COST, MAX_COST_CONSIDERED_SAFE
from app.utility import point_to_coord, get_coord_neighbors, get_absolute_distance, is_adjacent_to_coord


class PathFinder:
    def __init__(self, data, me):
        self.data = data
        self.me = me

        self.map_size = (data['width'], data['height'])

        self._finder = self._get_astar_pathfinder()

    # Determines the size of the safe area around a coord
    def flood_fill(self, start_coord, max_fill_size=None):
        explored = []
        queue = [start_coord]
        while queue:
            if max_fill_size is not None and len(explored) >= max_fill_size:
                return None

            next_coord = queue.pop(0)
            explored.append(next_coord)

            neighbors = self.get_valid_neighbors(next_coord)
            for neighbor in neighbors:
                if neighbor not in queue and neighbor not in explored:
                    queue.append(neighbor)

        return explored

    # Finds the best path to fill an area
    def get_best_path_fill(self, start_coord, max_path_length=None):
        def recurse_path(coord, path):
            current_path = list(path)
            current_path.append(coord)
            if max_path_length and len(current_path) >= max_path_length:
                return current_path
            neighbors = [neighbor for neighbor in self.get_valid_neighbors(coord) if neighbor not in current_path]
            if not neighbors:
                return current_path
            paths = []
            for neighbor in neighbors:
                new_path = recurse_path(neighbor, current_path)
                if max_path_length and len(new_path) >= max_path_length:
                    return new_path
                paths.append(new_path)
            return max(paths, key=lambda x: len(x))
        return recurse_path(start_coord, [])

    def _get_fatal_coords(self, foresight_distance=0):
        # Don't move into any coords where a snake body is,
        # unless we're far enough away that it won't be there when we get there
        # Our own head isn't fatal, since we can never move into it
        fatal_coords = [coord for snake_body in self.snake_bodies for coord in snake_body
                        if (coord not in [self.me.head, self.me.tail] or coord in self.me.body)
                        and (not self.me.has_trait(FORESIGHTED)
                        or len(snake_body) - (snake_body.index(coord) + 1) >=
                        min(get_absolute_distance(self.me.head, coord), len(snake_body), foresight_distance))]

        return fatal_coords

    # How far ahead we want to try and predict tail positions
    def set_foresight(self, foresight_distance):
        self.fatal_coords = self._get_fatal_coords(foresight_distance)

    # TODO: Not sure this is working the way I think. Node 1 and Node 2
    # Node cost calculation, which will make more dangerous paths cost more
    def get_cost(self, node1, node2):
        cost = 0

        # Pathing near walls costs more, unless we're trapped, then it's actually better
        adjacent_wall_count = len([c for i, c in enumerate(node2) if c == 0 or c == self.map_size[i] - 1])
        cost += adjacent_wall_count * self.me.dna(WALL_DANGER_COST)

        # Pathing near other snake's bodies is more expensive, based on how close to the head we are
        cost += sum([danger * self.me.dna(BODY_DANGER_COST) for coord, danger in self.body_danger if is_adjacent_to_coord(node2, coord)])

        # Pathing into squares adjacent to a snake head costs much more
        if node2 in self.head_danger_coords:
            cost += self.me.dna(HEAD_DANGER_COST)

        # Pathing into a small area costs more, based on how small it is compared to our length
        # If we're already trapped, and no moves make us "more" trapped, ignore the danger
        if (not self.is_trapped or len(set(self.coord_to_trap_danger.values())) > 1) \
                and node2 in self.coord_to_trap_danger.keys():
            cost += (1 - (self.coord_to_trap_danger[node2] / float(self.me.length))) * self.me.dna(TRAP_DANGER_COST)

        return max(cost, self.me.dna(BASE_COST))

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
        self.snake_bodies = [[point_to_coord(point) for point in snake['body']['data']]
                             for snake in self.data['snakes']['data']]

        self.fatal_coords = self._get_fatal_coords()

        # Used to calculate the danger in moving next to a snake, based on how close to the tail it is
        self.body_danger = [(coord, len(body) - index) for body in self.snake_bodies for index, coord in enumerate(body) if coord != self.me.head]

        # Avoid squares adjacent to enemy snake heads, since they're dangerous
        # Smaller snakes that we're directly adjacent to are safe, though
        other_snake_heads = [(point_to_coord(snake['body']['data'][0]), snake['length'] < self.me.length)
                            for snake in self.data['snakes']['data'] if snake['id'] != self.me.id]
        self.head_danger_coords = [neighbor for head, smaller in other_snake_heads for neighbor in
                                   get_coord_neighbors(head) if not (smaller and is_adjacent_to_coord(self.me.head, neighbor))]

        # Get valid moves
        self.valid_moves = self.get_valid_neighbors(self.me.head)

        # Find the size of the area we'd be moving into, for each valid move
        fill_coords = dict(
            [(move_coord, self.flood_fill(move_coord, self.me.length)) for move_coord in self.valid_moves])

        # If the area is smaller than our size (with multiplier), it's dangerous
        self.coord_to_trap_danger = dict(
            [(coord, len(fill)) for coord, fill in fill_coords.items() if fill])

        # We're enclosed in an area smaller than our body
        self.is_trapped = len(self.coord_to_trap_danger) == len(fill_coords)

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

    # Is this path safe enough for us to use?
    # A max of 0 means all paths are safe
    def path_is_safe(self, path, max_modifier=0):
        max_cost = self.me.dna(MAX_COST_CONSIDERED_SAFE)
        return True if max_cost == 0 else path[0] <= max_cost + max_modifier
