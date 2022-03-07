from click import command, group, echo, option, argument
from ..material_list import MaterialList, sort, localize, merge_dicts
from ..schematic_parse import Schematic


@group()
def cli():
    """This is the CLI for litematica-tools."""
    pass


# Define as command:
@cli.command('list')
@argument('file')
# Which categories to list:
@option('--blocks/--no-blocks', '-b/-B', 'blocks', default=False)
@option('--inventories/--no-inventories', '-i/-I', 'inventories', default=False)
@option('--entities/--no-entities', '-e/-E', 'entities', default=False)
# Options for the listing:
#@option('--blocks/--no-blocks', '-b/-B', 'blocks')
def list_schem(file, blocks, inventories, entities):
    """Options for counting and listing schematic contents."""
    if not (blocks or inventories or entities):
        blocks = True

    mat_list = MaterialList(Schematic(file)).composite_list(blocks, inventories, entities)

    echo(mat_list)
