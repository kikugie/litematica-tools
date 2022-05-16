import json
import logging
import os
from dataclasses import dataclass

logging.basicConfig(level=logging.DEBUG)


@dataclass(frozen=True)
class _Config:
    def __init__(self, configs: dict):
        self.__dict__.update(configs)


def load(filepath):
    with open(filepath, 'r') as f:
        logging.debug(f'Loading config file: {filepath}')
        return json.load(f)


files = ['block_items.json', 'excluded_display_names.json', 'ignored_blocks.json', 'name_references.json',
         'qstackables.json', 'unstackables.json']

CONFIG = _Config({v.split('.')[0]: load(os.path.join(os.path.dirname(__file__), v)) for v in files})
logging.debug(f'Loaded configs: {CONFIG.__dict__}')
