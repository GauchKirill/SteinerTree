# generate_tests.py
import json
import random

TESTS_NUM: int = 10
COORD_MIN: int = -40
COORD_MAX: int = 40
POINTS_MIN: int = 20
POINTS_MAX: int = 80

def generate_test(filename, num_terminals, seed):
    random.seed(seed)
    nodes = []
    for i in range(1, num_terminals + 1):
        x = random.randint(COORD_MIN, COORD_MAX)
        y = random.randint(COORD_MIN, COORD_MAX)
        nodes.append({"x": x, "y": y, "id": i, "type": "t"})
    with open(filename, 'w') as f:
        json.dump({"node": nodes}, f, indent=2)

if __name__ == '__main__':
    for i in range(TESTS_NUM):
        n = random.randint(POINTS_MIN, POINTS_MAX)
        generate_test(f"test{i}.json", n, i)