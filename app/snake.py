from app.constants import DEFAULT_DNA, PECKISH_THRESHOLD, STARVING_THRESHOLD
from app.utility import point_to_coord


class Snake:
    def __init__(self, data):
        # The snake's data
        self.id = data['id']
        self.name = data['name']
        self.length = data['length']
        self.health = data['health']
        self.coords = [point_to_coord(point) for point in data['body']['data']]
        self.head = self.coords[0]
        self.body = self.coords[1:-1] if self.length >= 3 else []
        self.tail = self.coords[-1]


class PlayerSnake(Snake):
    def __init__(self, data, dna_string, traits_string):
        # Get the basic snake info
        Snake.__init__(self, data['you'])

        # If no DNA is passed in, use the default values
        self._dna = dna_string.split('-') if dna_string else DEFAULT_DNA
        self._traits = traits_string.split('-')

        self.is_peckish = self.health < self.dna(PECKISH_THRESHOLD)
        self.is_starving = self.health < self.dna(STARVING_THRESHOLD)

    def has_trait(self, trait):
        return trait in self._traits

    # Get a particular piece of dna and convert to an int, if possible
    def dna(self, index):
        try:
            return int(self._dna[index])
        except ValueError:
            return self._dna[index]