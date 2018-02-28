# Turn a coord delta into a direction
# 0,0 is the top left of the map
DIRECTION_MAP = {
    (0, -1): 'up',
    (0, 1): 'down',
    (-1, 0): 'left',
    (1, 0): 'right'
}

# Traits
OPPORTUNISTIC = 'opp'
AGGRESSIVE = 'agg'
GLUTTONOUS = 'glu'
INSECURE = 'ins'
FORESIGHTED = 'for'
COOPERATIVE = 'coo'

# DNA
DEFAULT_DNA = [
    10,     # BASE_COST
    500,    # HEAD_DANGER_COST
    10,     # BODY_DANGER_COST
    50,     # WALL_DANGER_COST
    2000,   # TRAP_DANGER_COST
    400,    # MAX_COST_CONSIDERED_SAFE
    30,     # PECKISH_THRESHOLD
    10,     # STARVING_THRESHOLD
    20      # MAX_OPPORTUNISTIC_EAT_COST
]

# DNA indexes
BASE_COST = 0
HEAD_DANGER_COST = 1
BODY_DANGER_COST = 2
WALL_DANGER_COST = 3
TRAP_DANGER_COST = 4
MAX_COST_CONSIDERED_SAFE = 5
PECKISH_THRESHOLD = 6
STARVING_THRESHOLD = 7
MAX_OPPORTUNISTIC_EAT_COST = 8