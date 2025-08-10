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


def test_debug_program():
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
