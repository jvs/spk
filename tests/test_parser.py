from spk import parser


def test_tuple_literals():
    program = """
        w = (foo, bar, baz)
        x = (fizz, buzz)
        y = (zim,)
        z = ()
    """
    src = parser.parse(program)
    assert src and isinstance(src, list) and len(src) == 4
    assert all(isinstance(i, parser.Assign) for i in src)
    assert all(isinstance(i.value, parser.TupleLiteral) for i in src)

    w, x, y, z = [i.value.elements for i in src]
    assert w == ['foo', 'bar', 'baz']
    assert x == ['fizz', 'buzz']
    assert y == ['zim']
    assert z == []


def test_nested_tuple_literals():
    program = """
        x = ((),)
        y = (((),),)
        z = (())
    """
    src = parser.parse(program)
    assert src and isinstance(src, list) and len(src) == 3
    assert all(isinstance(i, parser.Assign) for i in src)
    assert all(isinstance(i.value, parser.TupleLiteral) for i in src)

    Tuple = parser.TupleLiteral
    empty = Tuple(elements=[])

    x, y, z = [i.value.elements for i in src]
    assert x == [empty]
    assert y == [Tuple(elements=[empty])]
    assert z == []


def test_comparison_operators():
    program = """
        x = foo in bar
        y = fiz not in buz
        z = zim in zam == flim not in flam
    """
    src = parser.parse(program)
    assert src and isinstance(src, list) and len(src) == 3
    assert all(isinstance(i, parser.Assign) for i in src)

    Op = parser.Infix
    x, y, z = [i.value for i in src]

    assert x == Op('foo', 'in', 'bar')
    assert y == Op('fiz', 'not in', 'buz')
    assert z == Op(Op('zim', 'in', 'zam'), '==', Op('flim', 'not in', 'flam'))


def test_simple_node():
    program = """
        node ComboComposerV1 {
            state {
                mode = "idle"
                keys = {}
            }
        }
    """
    src = parser.parse(program)
    assert src


def test_program_with_many_literals():
    program = """
        graph test-graph {
            node my-node {
                state {
                    is-pressed = false
                    deadline = 0 * ms
                    variable-name = initial-value
                    counter = 0
                    pressed-keys = {}
                    key-map = {
                        "a": "action-a",
                        "b": "action-b",
                        "c": "action-c",
                    }
                    empty-map = {:}
                    nonempty-set = {1, 2, 3}
                    some-list = [1, 2, 3]
                }

                on key(event) {
                    press "a"
                    is-pressed = true
                    deadline = event.time + 1000 * ms
                }

                on tick(event) {
                    if is-pressed and event.time > deadline {
                        release "a"
                        is-pressed = false
                        deadline = 0 * ms
                    }
                }
            }

            edges {
                input >> my-node >> output
            }
        }
    """
    src = parser.parse(program)
    assert src

    assert len(src) == 1
    graph = src[0]
    assert graph.name == 'test-graph'
    assert isinstance(graph, parser.Graph)
    assert len(graph.body) == 2

    node, edges = graph.body
    assert isinstance(node, parser.Node)
    assert node.name == 'my-node'
    assert len(edges.body) == 1
    assert edges.body[0].nodes == ['input', 'my-node', 'output']


def test_node_with_generic_types():
    program = """
        node Debouncer {
            config {
                debounce_delay: Duration = 50 * ms
            }

            state {
                # Keep a map of key to the last time it was pressed.
                last_pressed: Map<Key, Time> = {:}

                # Keep a set of the currently pressed keys, to prevent double-releases.
                is_pressed: Set<Key> = {}
            }

            on press(event) {
                last_time = state.last_pressed.get(event.key, 0)

                if event.time - last_time > config.debounce_delay {
                    state.last_pressed[event.key] = event.time
                    state.is_pressed << event.key
                    press event.key
                }
            }

            on release(event) {
                if event.key in state.is_pressed {
                    state.is_pressed.remove(event.key)
                    release event.key
                }
            }
        }
    """
    src = parser.parse(program)
    assert src and isinstance(src, list) and len(src) == 1
    debouncer = src[0]
    assert debouncer.name == 'Debouncer'
    config = debouncer.body[0]
    state = debouncer.body[1]

    debounce_delay = config.body[0]
    assert debounce_delay.name == 'debounce_delay'
    assert debounce_delay.type == 'Duration'

    last_pressed = state.body[0]
    assert last_pressed.name == 'last_pressed'
    assert last_pressed.type == parser.Postfix(
        'Map',
        parser.GenericArgumentList(['Key', 'Time']),
    )
