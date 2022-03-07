import time

from main import MaterialList, Schematic
from main.material_list import sort, localize

x = {}
times = []
start = time.time()
schem = Schematic('schematics/main_storage.litematic')
print(f'File: {schem.file}')
bmatl = localize(sort(MaterialList(schem).block_list()))
imatl = localize(sort(MaterialList(schem).item_list()))
ematl = localize(sort(MaterialList(schem).entity_list()))
tmatl = localize(sort(MaterialList(schem).totals_list()))
end = time.time()
times.append(end - start)

print(f'Blocks: {bmatl}')
print(f'Items: {imatl}')
print(f'Entities: {ematl}')
print(f'Totals: {tmatl}')

print(f'Total time: {sum(times) / len(times)} s')
