import json
import string

import unittest
from boddle import boddle

from app import main

# """
# ________
# ________
# ________
# ________
# ________
# ________
# ________
# ________
# """


class TestIt(unittest.TestCase):
  def setUp(self):
    self.snakes = {}
    self.you = {'id':'0', 'name': 'you', 'body': [], 'health': 100}

  def testMoveWall(self):
    with boddle(json=self.generateMoveRequest(
            """
             _Y__
             _0__
             _y__
             ____
             """
    )):
      moveResponse = main.move()
      self.assertNotEqual(moveResponse, '{"move": "up"}')

  def testMoveCorner(self):
    with boddle(json=self.generateMoveRequest(
            """
            Y___
            0___
            y___
            ____
            """
    )):
      moveResponse = main.move()
      self.assertEqual('{"move": "right"}', moveResponse)

  def testMoveEnemy(self):
    with boddle(json=self.generateMoveRequest(
            """
            _A1a
            _Y__
            _0__
            _y__
            """
    )):
      moveResponse = main.move()
      self.assertNotEqual('{"move": "up"}', moveResponse)

  def testMoveAvoidTrap(self):
    with boddle(json=self.generateMoveRequest(
            """
            ____y___
            _00_000_
            _00Y__0_
            _000000_
            ________
            ________
            ________
            ________
            """
    )):
      moveResponse = main.move()
      self.assertEqual('{"move": "up"}', moveResponse)

  def testMoveAvoidTrapOpp(self):
    with boddle(json=self.generateMoveRequest(
            """
            _______________
            __________y0_00
            ___________0000
            ______________0
            ______________0
            ______________0
            _____________00
            ________000000_
            ________0_____X
            ________0______
            ________0______
            ________0000___
            ___________00__
            ____________00X
            _______X__X__Y_
            """
    )):
      moveResponse = main.move(traits="opp")
      self.assertEqual('{"move": "left"}', moveResponse)

  def generateMoveRequest(self, asciiBoard):
    moveRequest = {}
    self.addToil(moveRequest)
    self.convert(moveRequest,
        asciiBoard
    )
    moveRequest['you'] = self.you
    return moveRequest

  def convert(self, moveRequest, asciiPicture):
    lines = asciiPicture.splitlines()[1:-1]

    moveRequest['board'] = {}
    moveRequest['board']['height'] = len(lines)
    moveRequest['board']['width'] = len(lines)
    moveRequest['board']['food'] = []
    moveRequest['board']['you'] = self.you
    for r_index, row in enumerate(lines):
        for c_index, char in enumerate(row.strip()):
            if char == '_':
                pass
            elif char == 'X':
                moveRequest['board']['food'].append({
                    'y': r_index,
                    'x': c_index
                })
            elif char == 'Y':
                moveRequest['board']['you']['head'] = {
                    'y': r_index,
                    'x': c_index
                }
            elif char == 'y':
                moveRequest['board']['you']['tail'] = {
                    'y': r_index,
                    'x': c_index
                }
            elif char == '0':
                moveRequest['board']['you']['body'].append({
                    'y': r_index,
                    'x': c_index
                })
            else:
                if char in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    char_index = string.ascii_lowercase.index(str.lower(char)) + 1
                    self.getOrCreateSnake(str(char_index))['head'] = {
                        'y': r_index,
                        'x': c_index
                    }
                elif char in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
                    char_index = string.ascii_lowercase.index(str.lower(char)) + 1
                    self.getOrCreateSnake(str(char_index))['tail'] = {
                        'y': r_index,
                        'x': c_index
                    }
                elif char in ['1', '2', '3', '4', '5', '6', '7']:
                    self.getOrCreateSnake(char)['body'].append({
                        'y': r_index,
                        'x': c_index
                    })

    moveRequest['board']['snakes'] = list(self.snakes.values())
    moveRequest['board']['snakes'].append(moveRequest['board']['you'])

    for snake in moveRequest['board']['snakes']:
        snake['body'].insert(0, snake.pop('head'))
        snake['body'].append(snake.pop('tail'))

    print('%s' % json.dumps(moveRequest))

  def getOrCreateSnake(self, id):
    if id not in self.snakes:
        self.snakes[id] = {'id': id, 'name': 'test-%s' % id}
        self.snakes[id]['body'] = []
    return self.snakes[id]

  def addToil(self, moveRequest):
    moveRequest['game'] = {'id': 'game1'}
    moveRequest['turn'] = 1


if __name__ == '__main__':
    unittest.main()