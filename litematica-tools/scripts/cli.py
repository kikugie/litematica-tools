from click import command, group, echo, option, argument
from ..material_list import MaterialList, sort, localize
from ..schematic_parse import Schematic


@group()
def cli():
    pass


@cli.command('list')
@argument('file')
def list_schem(file):
    mat_list = MaterialList(Schematic(file))
    mat_list.totals_list()
