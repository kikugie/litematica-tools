import json
import litematicparse

schem = litematicparse.Litematic('CCS_Raid_Full.litematic')
schem.write_json('test.json')

#print(schem.block_count())

print(schem.regions)


rg = 'Y:63, Chunk coords: 0, 0'

#print(schem.regions[rg].get_block(0, 0, 1))
print(schem.regions[rg].block_count())

for i in schem.regions[rg].block_iterator():
    print(i)
#
#
# blocks = schem.regions[rg].block_count()
# items = schem.regions[rg].inventory_count()
# entities = schem.regions[rg].entity_count()
# total = blocks + items + entities
#
# print(f"Blocks: {blocks.raw_counts}\n")
# print(f"Items: {items.raw_counts}\n")
# print(f"Entities: {entities.raw_counts}\n")
# print(f"Total: {total.raw_counts}")
#
# with open(f'blocks.json', 'w') as f:
#     json.dump(blocks.sorted_counts(), f, indent=2)
# with open('items.json', 'w') as f:
#     json.dump(items.sorted_counts(), f, indent=2)
# with open('entities.json', 'w') as f:
#     json.dump(entities.sorted_counts(), f, indent=2)
# with open('total.json', 'w') as f:
#     json.dump(total.sorted_counts(), f, indent=2)
