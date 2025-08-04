from . import errors, parser

Def = (parser.Class, parser.Function, parser.Graph, parser.Node)


class Environment:
    def __init__(self, parent, reporter):
        self.parent = parent
        self.reporter = reporter
        self.bindings = {}

    def bind(self, name, value) -> None:
        if name in self.bindings:
            self.reporter.error(
                errors.DuplicateDefinitions(name, self.bindings[name], value)
            )

        self.bindings[name] = value


class Program:
    def __init__(self, environment, reporter):
        self.environment = environment
        self.reporter = reporter


class Reporter:
    def __init__(self):
        self.errors = []
        self._next_id = 1

    def error(self, obj):
        self.errors.append(obj)

    def reserve_id(self):
        result = self._next_id
        self._next_id += 1
        return result


def create_program(parsed_objects: list[parser.ParsedObject]) -> Program:
    reporter = Reporter()
    environment = Environment(parent=None, reporter=reporter)

    _visit(
        parsed_objects=parsed_objects,
        environment=environment,
        reporter=reporter,
    )

    return Program(environment=environment, reporter=reporter)


def _visit(
    parsed_objects: list[parser.ParsedObject],
    environment: Environment,
    reporter: Reporter,
):
    for item in parsed_objects:
        item._metadata.object_id = reporter.reserve_id()

        if isinstance(item, parser.Assign):
            if isinstance(item.location, str) and item.operator == '=':
                environment.bind(item.location, item)
            else:
                reporter.error(errors.OnlySimpleAssignments(item))

        elif isinstance(item, Def):
            if item.name is None:
                reporter.error(errors.UnboundAnonymousItem(item))
            else:
                environment.bind(item.name, item)

            body = getattr(item, 'body', None)

            if body is not None:
                assert isinstance(body, list)

                item._metadata.environment = Environment(
                    parent=environment,
                    reporter=reporter,
                )

                _visit(
                    parsed_objects=body,
                    environment=item._metadata.environment,
                    reporter=reporter,
                )
