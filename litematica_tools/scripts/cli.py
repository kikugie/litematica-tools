import csv
import io
import json

from click import group, echo, option, argument, Choice
from ..material_list import MaterialList
from ..schematic_parser import NBTFile

item_name = "Item"
total_name = "Total"


# Root command
@group()
def cli():
    """This is the CLI for litematica-tools."""
    pass


# Define as command
@cli.command('list')
@argument('file')
# Which categories to list
@option('--blocks/--no-blocks', '-b/-B', 'blocks', default=False, help='Include blocks.')
@option('--inventories/--no-inventories', '-i/-I', 'inventories', default=False, help='Include inventory contents.')
@option('--entities/--no-entities', '-e/-E', 'entities', default=False, help='Include entities.')
# Output formatting option
@option('--format', '-f', 'formatting', default='basic',
        type=Choice(['basic', 'json', 'csv', 'ascii'], case_sensitive=False), help='Output format.')
def list_schem(file, blocks, inventories, entities, formatting):
    """Options for counting and listing schematic contents."""
    if not (blocks or inventories or entities):
        blocks = True

    mat_list = MaterialList(NBTFile(file)).composite_list(blocks=blocks, items=inventories, entities=entities)

    echo(format_list(mat_list, formatting))


def format_list(mat_list, formatting):
    out = ''
    match formatting:
        case 'basic':
            for k, v in mat_list.items():
                out += f'{k}: {v}\n'
        case 'json':
            out = json.dumps(mat_list, indent=4)
        case 'csv':
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow((item_name, total_name))
            writer.writerows([(k, v) for k, v in mat_list.items()])
            out = output.getvalue()
        case 'ascii':
            out = format_ascii(mat_list)
    return out


def format_ascii(mat_list):
    max_name_len = max(max([len(i) for i in mat_list.keys()]), len(item_name))
    max_amount_len = max(max([len(str(i)) for i in mat_list.values()]), len(total_name))

    def make_row(key, value):
        return '| {key}{key_spaces} | {value}{value_spaces} |\n'.format(
            key=key,
            value=value,
            key_spaces=' ' * (max_name_len - len(key)),
            value_spaces=' ' * (max_amount_len - len(str(value)))
        )

    divider = '+{dashes_left}+{dashes_right}+\n'.format(
        dashes_left='-' * (max_name_len + 2),
        dashes_right='-' * (max_amount_len + 2)
    )
    header = divider + make_row(item_name, total_name) + divider

    out = header
    for k, v in mat_list.items():
        out += make_row(k, v)
    out += header

    return out
