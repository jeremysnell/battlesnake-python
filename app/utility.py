from app.constants import DIRECTION_MAP


# Add two coord tuples together
def add_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x + y, coord_one, coord_two))


# Find the difference between two coord tuples
def sub_coords(coord_one, coord_two):
    return tuple(map(lambda x, y: x - y, coord_one, coord_two))


# Convert from x,y point dictionary to coord tuple
def point_to_coord(point):
    return point['x'], point['y']


# Get the four neighboring squares for a given coord (up, down, left, right)
def get_coord_neighbors(coord):
    return [add_coords(coord, dir_coord) for dir_coord in DIRECTION_MAP.keys()]


# Get absolute distance
def get_absolute_distance(coord1, coord2):
    diff = sub_coords(coord1, coord2)
    return abs(diff[0]) + abs(diff[1])


# Is the given coord adjacent to any of the given coords?
def is_adjacent_to_coords(coord, coords):
    return any([neighbor for neighbor in get_coord_neighbors(coord) if neighbor in coords])
