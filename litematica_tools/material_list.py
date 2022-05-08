import re
from dataclasses import dataclass, field

from litematica_tools.storage.shared_storage import Region, BlockState, Structure, ItemStack
from litematica_tools.utils import ItemCounter
from .config import CONFIG
from .structure_parser import NBTFile


@dataclass(kw_only=True)
class MatConfig:
    """
    Configuration class for the material list.
    """
    ignored_blocks: list = field(default_factory=list)
    ignored_names: list = field(default_factory=list)
    block_items: dict = field(default_factory=dict)
    excluded_names: list = field(default_factory=list)
    block_mode: bool = False
    water_logging: bool = True
    entity_items: bool = True

    def __post_init__(self, *n, **kw):
        if 'ignored_blocks' not in kw:
            self.ignored_blocks = CONFIG.ignored_blocks
        if 'block_items' not in kw:
            self.block_items = CONFIG.block_items
        if 'excluded_names' not in kw:
            self.excluded_names = CONFIG.excluded_display_names


class MaterialList:
    def __init__(self, structure: Structure, config: MatConfig = MatConfig()):
        self.structure = structure
        self.config = config
        self._block_list = None
        self._item_list = None
        self._entity_list = None

    @classmethod
    def from_file(cls, *args, **kwargs):
        return MaterialList(NBTFile(*args, **kwargs))

    @property
    def block_count(self):
        if self._block_list is not None:
            return self._block_list
        else:
            return self.list_blocks()

    @block_count.deleter
    def block_count(self):
        self._block_list = None

    def list_blocks(self, region: Region = None) -> ItemCounter:
        self._block_list = ItemCounter()
        if region is None:
            regions = list(self.structure.regions.values())
        else:
            regions = [region]

        for r in regions:
            palette = self._process_palette(r.palette)
            ignored_ids = [i for i, v in enumerate(r.palette) if v.name in self.config.ignored_blocks]
            for i, v in enumerate(r.block_iterator()):
                if v in ignored_ids:
                    continue
                self._block_list.extend(palette[v])
        return self._block_list

    def _process_palette(self, palette: list) -> list[dict[str, int]]:
        proc_palette = [{}] * len(palette)
        for i, b in enumerate(palette):
            if b.name in self.config.ignored_blocks:
                continue
            proc_palette[i] = self._process_block_state(b)
            if self.config.block_mode:
                continue
            block_item = self._process_block_item(b)
            if block_item is not None:
                del proc_palette[i][b.name]
                proc_palette[i].update(block_item)
        return proc_palette

    def _process_block_state(self, block_state: BlockState) -> dict[str, int]:
        entry: dict[str, int] = {block_state.name: 1}
        if block_state.properties is None:
            return entry
        if ('half', 'top') in block_state.properties:
            del entry[block_state.name]
        if self.config.block_mode:
            return entry
        if self.config.water_logging and ('waterlogged', 'true') in block_state.properties:
            entry['minecraft:water_bucket'] = 1
        if multiplier_property := list(block_state.properties.keys() & ['eggs', 'pickles', 'candles']):
            entry[block_state.name] = int(block_state.properties[multiplier_property[0]])
        return entry

    def _process_block_item(self, block_state: BlockState) -> dict[str, int]:
        if block_state.name not in self.config.block_items:
            return {block_state.name: 1}
        block_item = self.config.block_items[block_state.name]
        if isinstance(block_item, str):
            block_item = [block_item]
        return {i: 1 for i in block_item}

    @property
    def item_count(self):
        if self._item_list is not None:
            return self._item_list
        else:
            return self.list_items()

    @item_count.deleter
    def item_count(self):
        self._item_list = None

    def list_items(self, region: Region = None) -> ItemCounter:
        def filter_names(item_stack: ItemStack) -> bool:
            if item_stack.display_name is None:
                return True
            for i in self.config.excluded_names:
                if re.search(i, item_stack.display_name):
                    return False
            return True

        if region is None:
            regions = list(self.structure.regions.values())
        else:
            regions = [region]

        # Extract all items from all regions
        item_stack_list = []
        for r in regions:
            for i in r.tile_entities:
                item_stack_list.extend(i.rec_inventory)
            if self.config.entity_items:
                for i in r.entities:
                    item_stack_list.extend(i.rec_inventory)

        # Filter items by display name
        self._item_list = ItemCounter()
        item_stack_list = filter(filter_names, item_stack_list)
        for i in item_stack_list:
            self._item_list.append(i.name, i.count)
        # self._item_list = ItemCounter({i.name: i.count for i in filter(
        #     lambda item: any(re.search(m, item.display_name) for m in self.config.excluded_names), item_stack_list)})
        return self._item_list

    @property
    def entity_count(self):
        if self._entity_list is not None:
            return self._entity_list
        else:
            return self.list_entities()

    @entity_count.deleter
    def entity_count(self):
        self._entity_list = None

    def list_entities(self, region: Region = None) -> ItemCounter:
        if region is None:
            regions = list(self.structure.regions.values())
        else:
            regions = [region]

        # Extract all entities from all regions
        self._entity_list = ItemCounter()
        for r in regions:
            for i in r.entities:
                self._entity_list.append(i.id, 1)
        return self._entity_list

    @property
    def total_count(self):
        return self.block_count + self.item_count + self.entity_count

    def composite_list(self, blocks: bool, items: bool, entities: bool) -> ItemCounter:
        out = ItemCounter()
        if blocks:
            out.extend(self.block_count)
        if items:
            out.extend(self.item_count)
        if entities:
            out.extend(self.entity_count)
        return out
