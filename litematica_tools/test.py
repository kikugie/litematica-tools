import pprint
import time
import timeit

from material_list_2 import *


def matl():
    schem = NBTFile('main_storage.litematic')
    out = MaterialList(schem).item_list()
    return out

print(matl())
print(timeit.timeit(matl, number=1))
