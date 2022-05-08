import os
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class _Config:
    def __init__(self, configs: dict):
        self.__dict__.update(configs)


def load(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


_configs = {}
for root, _, files in os.walk(os.path.dirname(__file__)):
    for file in files:
        if file.endswith('.json'):
            _configs[os.path.splitext(file)[0]] = load(os.path.join(os.path.dirname(__file__), root, file))

CONFIG = _Config(_configs)
