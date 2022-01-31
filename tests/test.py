import json
import litematicparse

schem = litematicparse.Litematic('3x3 piston door.litematic')
schem.write_json('test.json')

print(schem.block_count())

print(schem.regions)


rg = '3x3 piston door'

print(schem.regions[rg].get_block(0, 1, 1))

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
