from spk import parser


def test_debug_program():
    program = """
        graph test-graph {
            node my_node {
                state {
                    is_pressed = false
                    deadline = 0 * ms
                    variable_name = initial_value
                    counter = 0
                    pressed_keys = {}
                    key_map = {
                        "a": "action_a",
                        "b": "action_b",
                        "c": "action_c",
                    }
                    empty_map = {:}
                    nonempty_set = {1, 2, 3}
                    some_list = [1, 2, 3]
                }

                on key(event) {
                    press "a"
                    is_pressed = true
                    deadline = event.time + 1000 * ms
                }

                on tick(event) every 1 * ms {
                    if is_pressed and event.time > deadline {
                        release "a"
                        is_pressed = false
                        deadline = 0 * ms
                    }
                }
            }

            edges {
                input >> my_node >> output
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
    assert isinstance(node, parser.NodeDefinition)
    assert node.name == 'my_node'
    assert len(edges) == 1
    assert edges[0].nodes == ['input', 'my_node', 'output']
