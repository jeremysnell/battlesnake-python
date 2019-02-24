from app.utility import point_to_coord


class Snake(object):
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.health = data['health']
        self.body = [point_to_coord(point) for point in data['body']]
        self.length = len(self.body)
        self.head = self.body[0]
        self.tail = self.body[-1]
