import time
import timeit

from litematica_tools import MaterialList, NBT_File
from litematica_tools.material_list import localise, dsort

def matl():
    schem = NBT_File('schematics/main_storage.litematic')
    return MaterialList(schem).block_list()

print(timeit.timeit(matl, number=1))