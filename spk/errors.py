from dataclasses import dataclass
from typing import Any

from . import parser


@dataclass
class DuplicateDefinitions:
    name: str
    previous_value: Any
    next_value: Any


@dataclass
class OnlySimpleAssignments:
    assign: parser.Assign | parser.Variable


@dataclass
class UnboundAnonymousItem:
    item: parser.ParsedObject
