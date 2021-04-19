from random import randint
from pprint import pprint


def generate_data(*, u=5, p=5, my_user=False):
    products = ['product' + str(i + 1) for i in range(p)]

    users = {'user' + str(j + 1):
             {products[i]: randint(0, 2) for i in range(p)}
             for j in range(u)}

    if my_user:
        users['My user'] = {products[i]: randint(0, 2) for i in range(p)}

    with open("data.py", "w") as f:
        f.write("USERS = ")
        pprint(users, f)
