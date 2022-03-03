import time

from main import Schematic, MaterialList
from main.material_list import sort, localize

x = {}
times = []
for i in range(1):
    start = time.time()
    schem = Schematic('main_storage.litematic')
    print(f'File: {schem.file}')
    bmatl = localize(sort(MaterialList(schem).block_list()))
    imatl = localize(sort(MaterialList(schem).item_list()))
    ematl = localize(sort(MaterialList(schem).entity_list()))
    end = time.time()
    times.append(end - start)

    print(f'Blocks: {bmatl}')
    print(f'Items: {imatl}')
    print(f'Entities: {ematl}')

print(f'Total time: {sum(times) / len(times)} s')


