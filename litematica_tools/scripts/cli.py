import csv
import io
import json

from click import command, group, echo, option, argument, Choice
from ..material_list import MaterialList
from ..schematic_parse import Schematic


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
# Options for the listing
#@option('--blocks/--no-blocks', '-b/-B', 'blocks') TODO
# Output formatting option
@option('--format', '-f', 'formatting', default='basic',
        type=Choice(['basic', 'json', 'csv', 'ascii'], case_sensitive=False), help='Output format.')
def list_schem(file, blocks, inventories, entities, formatting):
    """Options for counting and listing schematic contents."""
    if not (blocks or inventories or entities):
        blocks = True

    mat_list = MaterialList(Schematic(file)).composite_list(blocks, inventories, entities)

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
        return "| " + key + " " * (max_name_len - len(key)) + " | " + \
               str(value) + " " * (max_amount_len - len(str(value))) + " |\n"

    divider = "+" + "-" * (max_name_len + 2) + "+" + "-" * (max_amount_len + 2) + "+\n"
    header = divider + make_row(item_name, total_name) + divider

    out = header
    for k, v in mat_list.items():
        out += make_row(k, v)
    out += header

    return out

