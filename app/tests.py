import json
import string

import unittest
from boddle import boddle

from app import main


class TestIt(unittest.TestCase):
    def setUp(self):
        self.snakes = {}
        self.you = {'id': '0', 'name': 'you', 'body': [], 'health': 100}

    def testMoveWall(self):
        with boddle(json=self.generateMoveRequest(
                """
                 _Y__
                 _0__
                 _y__
                 ____
                 """
        )):
            move_response = main.move()
            self.assertNotEqual('{"move": "up"}', move_response.body)

    def testMoveCorner(self):
        with boddle(json=self.generateMoveRequest(
                """
                Y___
                0___
                y___
                ____
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveEnemy(self):
        with boddle(json=self.generateMoveRequest(
                """
                _A1a
                _Y__
                _0__
                _y__
                """
        )):
            move_response = main.move()
            self.assertNotEqual('{"move": "up"}', move_response.body)

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
            move_response = main.move()
            self.assertEqual('{"move": "up"}', move_response.body)

    def testMoveAvoidTrap2(self):
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
            move_response = main.move()
            self.assertEqual('{"move": "left"}', move_response.body)

    def testMoveAvoidTrap3(self):
        with boddle(json=self.generateMoveRequest(
                """
                ______000_
                ____000_00
                ____0__Y_y
                ____0__0__
                ____0__00_
                __000___0_
                __0_____00
                __00_000_0
                ___000_000
                __________
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveChooseLargerTrap(self):
        with boddle(json=self.generateMoveRequest(
                """
                _0000__Y0_
                00__000_0_
                0_____0_00
                0_____0__0
                0_____00_0
                0__y0__0_0
                0___0000_0
                0__000__00
                00_0_0000_
                _000______
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "down"}', move_response.body)

    def testMoveTailInsteadOfTrap(self):
        with boddle(json=self.generateMoveRequest(
                """
                ___0000___
                __00__0___
                _00_000___
                Y0__0_____
                y_000_____
                0000______
                00_00000__
                0______0__
                00000000__
                __________
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "down"}', move_response.body)

    def testMoveIntoOpenSpace(self):
        with boddle(json=self.generateMoveRequest(
                """
                __________
                __________
                __________
                ___000____
                _000_0__y_
                _0__00__0_
                00__Y___0_
                0_0000_00_
                000__000__
                00________
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveEatWhenStarving(self):
        move_request = self.generateMoveRequest(
                """
                ____
                X_Yy
                __00
                ____
                """
        )

        move_request['you']['health'] = 5

        with boddle(json=move_request):
            move_response = main.move()
            self.assertEqual('{"move": "left"}', move_response.body)

    def testMoveEatWhenTrappedAndPeckish(self):
        move_request = self.generateMoveRequest(
                """
                00X_
                00Yy
                0000
                0000
                """
        )

        move_request['you']['health'] = 15

        with boddle(json=move_request):
            move_response = main.move()
            self.assertEqual('{"move": "up"}', move_response.body)

    def testMoveDontEatWhenNextToTail(self):
        with boddle(json=self.generateMoveRequest(
                """
                000_
                0_Yy
                0_X0
                0000
                """
        )):
            move_response = main.move(traits="opp")
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveAvoidAdjacentStackedTail(self):
        move_request = self.generateMoveRequest(
                """
                0Y__
                0y__
                ____
                ____
                """
        )

        # Create a stacked tail, as if we just ate
        move_request['you']['body'].append(move_request['you']['body'][-1])

        with boddle(json=move_request):
            move_response = main.move(traits="ins")
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveTowardsStackedTail(self):
        move_request = self.generateMoveRequest(
                """
                _00000000_
                _000000000
                __Y__000_0
                __00_000_0
                ___0___0_0
                _000___0_0
                _0___y00_0
                00_______0
                0_0000__00
                000__0000_
                """
        )

        # Create a stacked tail, as if we just ate
        move_request['you']['body'].append(move_request['you']['body'][-1])

        with boddle(json=move_request):
            move_response = main.move()
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveTowardsStackedTail2(self):
        move_request = self.generateMoveRequest(
                """
                0Y__
                0y__
                ____
                ____
                """
        )

        # Create a stacked tail, as if we just ate
        move_request['you']['body'].append(move_request['you']['body'][-1])

        with boddle(json=move_request):
            move_response = main.move(traits="ins")
            self.assertEqual('{"move": "right"}', move_response.body)

    def testMoveAvoidEnemyHead(self):
        with boddle(json=self.generateMoveRequest(
                """
                __A1
                _Y0a
                __y_
                ____
                """
        )):
            move_response = main.move()
            self.assertEqual('{"move": "down"}', move_response.body)

        # TODO add trapped tail test
        # TODO add food when starving and trapped test

    def generateMoveRequest(self, asciiBoard):
        moveRequest = {}
        self.addToil(moveRequest)
        self.convert(moveRequest, asciiBoard)
        return moveRequest

    def convert(self, moveRequest, asciiPicture):
        lines = asciiPicture.splitlines()[1:-1]

        moveRequest['you'] = self.you
        moveRequest['board'] = {}
        moveRequest['board']['height'] = len(lines)
        moveRequest['board']['width'] = len(lines)
        moveRequest['board']['food'] = []
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
                    moveRequest['you']['head'] = {
                        'y': r_index,
                        'x': c_index
                    }
                elif char == 'y':
                    moveRequest['you']['tail'] = {
                        'y': r_index,
                        'x': c_index
                    }
                elif char == '0':
                    moveRequest['you']['body'].append({
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
        moveRequest['board']['snakes'].append(moveRequest['you'])

        for snake in moveRequest['board']['snakes']:
            snake['body'].insert(0, snake.pop('head'))
            snake['body'].append(snake.pop('tail'))

        print('%s' % json.dumps(moveRequest))

    def getOrCreateSnake(self, id):
        if id not in self.snakes:
            self.snakes[id] = {'id': id, 'name': 'test-%s' % id, 'health': 100}
            self.snakes[id]['body'] = []
        return self.snakes[id]

    def addToil(self, moveRequest):
        moveRequest['game'] = {'id': 'game1'}
        moveRequest['turn'] = 1


if __name__ == '__main__':
    unittest.main()
