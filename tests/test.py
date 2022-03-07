import time

from main import MaterialList, Schematic, Counter

x = {}
times = []
start = time.time()
schem = Schematic('schematics/main_storage.litematic')
print(f'File: {schem.file}')
bmatl = MaterialList(schem).block_list().csort().localise().data
imatl = MaterialList(schem).item_list().csort().localise().data
ematl = MaterialList(schem).entity_list().csort().localise().data
tmatl = MaterialList(schem).totals_list().csort().localise().data
end = time.time()
times.append(end - start)

print(f'Blocks: {bmatl}')
print(f'Items: {imatl}')
print(f'Entities: {ematl}')
print(f'Totals: {tmatl}')

print(f'Total time: {sum(times) / len(times)} s')
