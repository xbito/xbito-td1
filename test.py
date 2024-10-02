import unittest


class TestEnemy(unittest.TestCase):
    def test_enemy_movement(self):
        path = [(0, 0), (100, 0)]
        enemy = Enemy(path)
        enemy.move()
        self.assertGreater(enemy.x, 0)
        self.assertEqual(enemy.y, 0)


if __name__ == "__main__":
    unittest.main()
