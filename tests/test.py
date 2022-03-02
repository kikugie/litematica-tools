import json
import time

from litematic_parser import Schematic, MaterialList




times = []
decoder_times = []
list_times = []
for i in range(1):
    start = time.time()
    schem = Schematic('main_storage.litematic')
    raw_matl = MaterialList(schem.regions['main_storage'])
    matl = raw_matl.block_list()
    end = time.time()
    times.append(end-start)
    decoder_times.append(schem.regions['main_storage'].times)
    list_times.append(raw_matl.times)
print(f'Total time: {sum(times)/len(times)} s')

decoder_times = [j for sub in decoder_times for j in sub]
print(f'Decoder time: {sum(decoder_times)/len(decoder_times)} s')

list_times = [j for sub in list_times for j in sub]
print(f'List time: {sum(list_times)/len(list_times)} s')

# x = dict(sorted(matl.items(), key=lambda item: item[1], reverse=True))
#
# with open('ms.json', 'w') as f:
#     json.dump(x, f, indent=2)
