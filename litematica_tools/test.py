import sys
import timeit

from schematic_parse import NBTFile
from material_list import MaterialList
from shared_storage import Vector


def L_matl():
    schem = NBTFile('../tests/schematics/sample.litematic')
    matl = MaterialList(schem).block_list()
    # matl = MaterialList(schem).item_list()
    # print(matl)
    # matl = MaterialList(schem).entity_list()
    # print(matl)


def S_matl():
    schem = NBTFile('msmp.schem')
    # matl = MaterialList(schem).block_list()
    matl = MaterialList(schem).item_list()
    print(matl)


def N_matl():
    schem = NBTFile('sample.nbt')

#
print(timeit.timeit(L_matl, number=1))
print(timeit.timeit(S_matl, number=1))
# print(timeit.timeit(N_matl, number=1_000))
