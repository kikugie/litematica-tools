import time
import timeit

from litematica_tools import *

def L_matl():
    schem = NBTFile('schematics/sample.litematic')
    matl = MaterialList(schem).block_list()
    print(matl)
    # matl = MaterialList(schem).item_list()
    # print(matl)
    # matl = MaterialList(schem).entity_list()
    # print(matl)


def S_matl():
    schem = NBTFile('schematics/sample.schem')
    matl = MaterialList(schem).block_list()
    print(matl)
    # matl = MaterialList(schem).item_list()
    # print(matl)
    # matl = MaterialList(schem).entity_list()
    # print(matl)

def N_matl():
    schem = NBTFile('schematics/sample.nbt')
    matl = MaterialList(schem).block_list()
    print(matl)
    # matl = MaterialList(schem).item_list()
    # print(matl)
    # matl = MaterialList(schem).entity_list()
    # print(matl)


print(timeit.timeit(L_matl, number=1))
print(timeit.timeit(S_matl, number=1))
print(timeit.timeit(N_matl, number=1))
