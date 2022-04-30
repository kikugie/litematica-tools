import timeit
from pprint import pprint

from litematica_tools.storage import Litematic, Schem
from litematica_tools import MaterialList, NBTFile

def lmatl():
    lt = NBTFile('schematics/test.litematic')
    lmatl = MaterialList(lt)
    # print(lmatl.block_count.localise().sort())
    print(lmatl.item_count.localise().sort().get_stacks())
    # print(lmatl.entity_count)

# sc = NBTFile('schematics/test.schem')
# smatl = MaterialList(sc)
# # print(smatl.block_count)
# # print(smatl.item_count)
# # print(smatl.entity_count)
#
# nb = NBTFile('schematics/test.nbt')
# nmatl = MaterialList(lt)
# print(nmatl.block_count)
# print(nmatl.item_count)
# print(nmatl.entity_count)

# print(lmatl.block_count == smatl.block_count == nmatl.block_count)
# print(lmatl.item_count == smatl.item_count == nmatl.item_count)
# print(lmatl.entity_count == smatl.entity_count == nmatl.entity_count)

print(timeit.timeit(lmatl, number=1))