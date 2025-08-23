from __future__ import annotations
from . import errors, parser

Def = (parser.Class, parser.Function, parser.Graph, parser.Node)


class Environment:
    def __init__(self, parent: Environment | None):
        self.parent = parent
        self.reporter = parent.reporter if parent else Reporter()
        self.definitions = {}

    def define(self, name: str, value: parser.ParsedObject) -> None:
        if name in self.definitions:
            self.reporter.error(errors.DuplicateDefinitions(name, self.definitions[name], value))

        self.definitions[name] = value

    def lookup(self, name):
        if name in self.definitions:
            return self.definitions[name]
        elif self.parent is not None:
            return self.parent.lookup(name)
        else:
            return None


class Program:
    def __init__(self, environment: Environment):
        self.environment = environment


class Reporter:
    def __init__(self):
        self.errors = []
        self._next_id = 1

    def error(self, obj):
        self.errors.append(obj)

    def reserve_id(self) -> int:
        result = self._next_id
        self._next_id += 1
        return result


def create_program(parsed_objects: list[parser.ParsedObject]) -> Program:
    root_environment = Environment(parent=None)
    reporter = root_environment.reporter

    # Assign each parsed object a unique ID.
    for obj in parser.visit(parsed_objects):
        obj._metadata.object_id = reporter.reserve_id()

    # Create a tree of environments.
    environment_stack = [root_environment]
    environment = environment_stack[-1]
    for info in parser.traverse(parsed_objects):
        parent, child = info.parent, info.child

        if not info.is_finished:
            if isinstance(child, parser.Variable):
                if isinstance(child.names, list):
                    environment.reporter.error(errors.OnlySimpleAssignments(child))
                else:
                    environment.define(child.names.name, child)

            elif isinstance(child, Def) or isinstance(child, parser.Template):
                environment.define(child.name, child)

            elif isinstance(child, parser.Reference):
                child._metadata.environment = environment

        if _creates_new_environment(info):
            if info.is_finished:
                environment_stack.pop()
            else:
                environment_stack.append(Environment(parent=environment))

            environment = environment_stack[-1]

    assert environment is root_environment

    for obj in parser.visit(parsed_objects):
        if isinstance(obj, parser.Reference):
            environment = obj._metadata.environment
            obj._metadata.references = environment.lookup(obj.name)

    return Program(environment=root_environment)


def _creates_new_environment(info):
    return (
        isinstance(
            info.child,
            (
                parser.Class,
                parser.Config,
                parser.Function,
                parser.Graph,
                parser.Handler,
                parser.Node,
                parser.Globals,
                parser.State,
                parser.Template,
            ),
        )
        or (
            isinstance(
                info.parent,
                (
                    parser.Function,
                    parser.Handler,
                    parser.Template,
                    parser.For,
                ),
            )
            and info.field == 'body'
        )
        or (
            isinstance(info.parent, parser.If)
            and isinstance(info.child, list)
            and info.field in ['then_branch', 'else_branch']
        )
    )
