import time

from litematica_tools import MaterialList, NBT_File
from litematica_tools.material_list import localise, dsort

x = {}
times = []
start = time.time()
schem = NBT_File('schematics/test1.schem')
print(f'File: {schem.file}')
bmatl = localise(dsort(MaterialList(schem).block_list()))
imatl = localise(dsort(MaterialList(schem).item_list()))
ematl = localise(dsort(MaterialList(schem).entity_list()))
tmatl = localise(dsort(MaterialList(schem).totals_list()))
end = time.time()
times.append(end - start)

print(f'Blocks: {bmatl}')
print(f'Items: {imatl}')
print(f'Entities: {ematl}')
print(f'Totals: {tmatl}')

print(f'Total time: {sum(times) / len(times)} s')
