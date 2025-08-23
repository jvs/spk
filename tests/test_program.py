from spk import program, parser


def test_reference_resolution():
    """Test that references are correctly resolved to their definitions."""
    # Create a simple program with definitions and references
    program_text = """
        x = 42
        function my_func() {
            result = x
        }
        y = my_func
    """

    # Parse the program
    parsed_objects = parser.parse(program_text)

    # Create the program (this processes references)
    prog = program.create_program(parsed_objects)

    # Collect all reference nodes
    references = []
    for obj in parser.visit(parsed_objects):
        if isinstance(obj, parser.Reference):
            assert obj.name not in references
            references.append(obj)

    # Should find 2 references: one to x, one to my_func
    assert len(references) == 2

    # Find the references by name
    x_ref = None
    my_func_ref = None
    for ref in references:
        if ref.name == 'x':
            x_ref = ref
        elif ref.name == 'my_func':
            my_func_ref = ref

    assert x_ref is not None, 'Should find reference to x'
    assert my_func_ref is not None, 'Should find reference to my_func'

    # Check that references point to correct definitions
    assert x_ref._metadata.references is not None, 'x reference should be resolved'
    assert isinstance(x_ref._metadata.references, parser.Variable), (
        'x should reference the vairable'
    )
    assert x_ref._metadata.references.names.name == 'x'

    assert my_func_ref._metadata.references is not None, 'my_func reference should be resolved'
    assert isinstance(my_func_ref._metadata.references, parser.Function), (
        'my_func should reference the function'
    )
    assert my_func_ref._metadata.references.name == 'my_func'


def test_unresolved_reference():
    """Test that unresolved references have None in _metadata.references."""
    program_text = """
        x = undefined_var
    """

    parsed_objects = parser.parse(program_text)
    prog = program.create_program(parsed_objects)

    # Find the reference
    references = [x for x in parser.visit(parsed_objects) if isinstance(x, parser.Reference)]

    assert len(references) == 1
    undefined_ref = references[0]
    assert undefined_ref._metadata.references is None, 'Undefined reference should resolve to None'

    resolved = prog.environment.lookup('x')
    assert isinstance(resolved, parser.Variable)
    assert resolved.value == undefined_ref
