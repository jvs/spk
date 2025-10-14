# spk

## Overview

This document describes a domain-specific language (DSL) for composing stream
processors that handle keyboard events. The DSL aims to provide a nice
abstraction for keyboard firmware logic that can compile to C code for
integration with QMK, ZMK, or hid-remapper.

## Type System


- **Bit**: `1` or `0`, equivalent to `true` and `false`. (**Bool** is an alias for **Bit**.)
- **I8**, **I16**, **I32**, **I64**: signed integers.
- **U8**, **U16**, **U32**, **U64**: unsigned integers.
- **Time**: a number representing a time value.
- **Duration**: a number representing a duration value.
- **Symbol**: an opaque type, compiled to some integer value. Represented in
source code as character sequences surrounded by double-quotes (like strings in
other programming languages).
- **Key**: a `Symbol` for a key on a keyboard.
- **Event**: a key press, key release, or clock tick event.
- **Set<T>**: a generic set of elements of the same type.
- **List<T>**: a generic list of elements of the same type.
- **Map<K, V>**: a generic map of key-value pairs.
- **Tuple<I, J, K, ...>**: a tuple of elements of potentially different types.
- **Node**: a stream processing node.
- **Graph**: a graph of stream processing nodes.
- **Function<Tuple<A, B, C>, R>**: a function that takes arugments of types
A, B, and C and returns a value of type R.


## Syntax

- The syntax for spk is defined in the file grammar.txt. It is fairly conventional.
- Curly braces surround code blocks.
- Statements are separated by newlines.
- Comments begin with `#` and end with a newline.
- Symbols look like string literals, but each symbol is compiled to number. A
Symbol value does not have length property, for example, or any other traditional
string functions.


## Event Model

### Event Types

Key press events:
```
    {
        type: "press",
        key: Symbol,
        time: Time,
        counter: U32,
    }
```

Key release events:
```
    {
        type: "release",
        key: Symbol,
        time: Time,
        counter: U32,
    }
```

Clock tick events:
```
    {
        type: "tick",
        time: Time,
        counter: U32,
    }
```

A new clock tick events fires once every 1ms.


### Timing Semantics

All emitted events use current system time (not original event time).
This ensures temporal consistency and prevents timing bugs.

## Core Language Constructs

### Nodes

Nodes define stream processors. Each node processes a stream of events and may
emit new events.

A node has a name, optional configuration values, optional state values, a set
of functions, a set of event handlers, and a set of output ports. Any of these
sets may be empty. Nodes may be connected together by edges in a graph.

A simple example to show the basic structure:

```
# When active, this node maps "." to "!".
node Shout {
    state {
        is_active = false
    }

    on press(event) {
        # Toggle the state each time CapsLock is pressed.
        if event.key == "CapsLock" {
            state.is_active = not state.is_active
        }

        # Map "." to "!" when this node is active. Otherwise, emit the event as-is.
        if event.key == "." and state.is_active {
            press "!"
        } else {
            press event.key
        }
    }

    on release(event) {
        if event.key == "." and state.is_active {
            release "!"
        } else {
            release event.key
        }
    }
}
```

A more complex example:

```
# This node lets you build up a combo of multiple keys, one key at a time.
node ComboComposerV1 {
    state {
        mode = "idle"
        keys = {}
        deadline = 0
    }

    on press(event) {
        if event.key == "compose-combo" {
            if state.mode == "idle" {
                state.mode == "starting"
                state.keys = {}
            }
        } else if state.mode == "idle" {
            press event.key
        } else {
            state.keys << event.key
        }
    }

    on release(event) {
        if event.key == "compose-combo" {
            if state.mode == "starting" {
                state.mode = "recording"
            } else {
                state.mode = "pressing"
                state.deadline = current_time() + 10 * ms
                press_combo()
            }
        } else if state.mode == "idle" {
            release event.key
        }
    }

    on tick(event) {
        if state.mode == "pressing" and event.time >= state.deadline {
            release_combo()
            state.mode == "idle"
            state.keys = {}
        }
    }

    function press_combo() {
        for key in state.keys if is_modifier(key) { press key }
        for key in state.keys if not is_modifier(key) { press key }
    }

    function release_combo() {
        for key in state.keys if not is_modifier(key) { release key }
        for key in state.keys if is_modifier(key) { release key }
    }
}
```

#### Emitting Events

A node may emit "press" and "release" events. A node may also emit a key event
without knowing whether it is a "press" or a "release".

Some examples:

```
node Example {
    on key(event) {
        # Emit a "press" event using the "a" key.
        press "a"

        # Emit a "release" event using the "b" key.
        release "b"

        # Emit the event using its action, which is either "press" or "release".
        emit event.action(event.key)
    }
}
```

Whenever a node emits an event, the event's `time` field is set to the current
time, and the event's `counter` field is set to the current value of a global
counter that gets incremented on each event. (It wraps to 1 after reaching
`max_uint32`.)

A node may emit an event to a named output port. Output ports do not need to be
declared. The node can just refer to them, and the compiler will infer them.

```
node Router {
    state {
        mode = "idle"
    }

    on key(event) {
        if state.mode == "idle" {
            press "a" to some_port
            emit event.action(event.key) to other_port
        } else {
            release "b" to foo
            emit event.action(event.key) to bar
        }
    }
}
```

In this example, the Router node has four ports: `some_port`, `other_port`,
`foo`, and `bar`.

#### State Management

- State variables declared in state block with initial values.
- Support all the types described above: numbers, symbols, booleans, maps, sets, lists.
- State accessed via `state.` prefix, or its name, for named `state` sections.
- State is local to each node object.
- Each node section defines a singleton `Node` object.

#### More Details

- A node may have multiple event handlers with the same type. For example, a
node may have more than one `on press(event)` handlers. They are all called for
any applicable event. They are called in the order in which they are defined.
- A node may have a handler for all key events: `on key(event)`. This handler
is called for each "press" event and each "release" event. The `event.action`
property can be used to test which kind of event it is.
- Each node is a singleton object of type `Node`.
- A node is a first class value. It may be assigned to a variable.
- A node can have multiple `state` sections, for organization. Each state section
can optionally have a name, for disambiguation.
- A node can have one or more `config` sections, which may also optionally be
named. A config section is similar to a `state` section, only the compiler
verifies that no data in any config section is mutated or deleted.

### Graphs

Graphs define a set of nodes and edges. An edge connects the output of one node
to the input of another. Graphs can also have configuration data, functions,
and state.

A simple example to show the basic structure:

```
graph Pipeline {
    state shared {
        is_active = false
    }

    node Mapper {
        on key(event) {
            if event.key == "a" {
                emit event.action("A")
            } else if event.key == "b" {
                shared.is_active = true
            } else {
                emit event.action(event.key)
            }
        }
    }

    node Expander {
        on key(event) {
            if event.key == "tab" and shared.is_active {
                emit event.action(" ")
                emit event.action(" ")
                emit event.action(" ")
                emit event.action(" ")
            } else {
                emit event.action(event.key)
            }
        }
    }

    edges {
        input >> Mapper >> Expander >> output
    }
}
```

- The `input` and `output` elements define how this graph may be connected to
other graphs and nodes.
- The special graph called `main` runs as the main program. In this case, the
`input` and `output` elements connect the graph to the host system, like QMK,
ZMK, or hid-remapper.
- The `edges` section may have multiple lines, each line connecting a sequence
of nodes or subgraphs.
- Like nodes, graphs are first class values and may be assigned to variables.
- Also like nodes, each graph defines a singleton `Graph` object.

### Edges

A graph may contain multiple `edge` sections for organization.

Each `edge` section may contain conditional subsections. Events will only
flow along these edges when the condition evaluates to true. For example:

```
graph VimEmulator {
    state vim {
        mode = "normal"
    }

    # ... Imagine various nodes are defined here ...

    edges {
        if vim.mode == "normal" {
            input >> preprocessor >> normal_layer >> translator >> output
        }

        if vim.mode == "insert" {
            input >> debouncer >> escape_handler
            escape_handler.in_band >> insert_layer >> output
        }
    }
}
```

Whenever an event is emitted, the condition for each subsection is evaluated. If
the condition evaluates to `false`, then the event is not sent along any edge
in that subsection.

(Note, this example also shows how a graph can connect an output port to another
node. The expression `escape_handler.in_band` refers to an output port.)

## Templates

A library may define `template` functions that take normal values and return
new `node` or `graph` objects.

Templates:
- can only be called at compile-time, and cannot be called at run-time.
- can return new nodes and graphs.
- can call other templates.
- can call pure functions at compile-time.
- (A pure function doesn't mutate any `state` variables and doesn't emit any events.)

## Classes

spk supports simple data-transfer style classes. A class is a list of named,
typed fields.

For example,

```
class Combo {
    input_keys: Set<Key>
    output_key: Key
}
```

This class has two fields: `input_keys` and `output_key`. Each field is also
annotated with its type.

Classes are instantiated by calling the class name like a function:

```
escape_combo = Combo({"j", "k"}, "escape")
```


## Examples

### Layers

There are few ways to implement layers.

#### Conditional Edges

One way to implement layers is to define conditional edges. For example:

```
graph main {
    config {
        nav_key = "left alt"
        sym_key = "right alt"
    }

    global {
        layer = "normal"
    }

    node router {
        on press(event) {
            if global.layer != "normal" {
                press event.key
                return
            }

            match event.key {
                case config.nav_key { global.layer = "nav" }
                case config.sym_key { global.layer = "sym" }
                case * { press event.key }
            }
        }

        on release(event) {
            if global.layer == "nav" and event.key == config.nav_key {
                global.layer = "normal"
            } else if global.layer == "sym" and event.key == config.sym_key {
                global.layer = "normal"
            } else {
                release event.key
            }

        }
    }

    node normal {
        # ... Imagine state and handlers here ...
    }

    node nav {
        # ... Imagine state and handlers here ...
    }

    node sym {
        # ... Imagine state and handlers here ...
    }

    edges {
        # Always connect the input to the router node.
        input >> router

        if shared.layer == "normal" {
            router >> normal >> output
        }

        if shared.layer == "nav" {
            router >> nav >> output
        }

        if shared.layer == "sym" {
            router >> sym >> output
        }
    }
}
```

#### Node References

Another way to implement layers is to use node references. For example:

```
graph main {
    config {
        nav_key = "left alt"
        sym_key = "right alt"
    }

    global {
        layer = normal
    }

    node router {
        on press(event) {
            if global.layer != normal {
                # Send the event directly to the current layer node.
                press event.key to global.layer
                return
            }

            match event.key {
                case config.nav_key { global.layer = nav }
                case config.sym_key { global.layer = sym }
                case * { press event.key to global.layer }
            }
        }

        on release(event) {
            if global.layer == nav and event.key == config.nav_key {
                global.layer = normal
            } else if global.layer == sym and event.key == config.sym_key {
                global.layer = normal
            } else {
                # Send the event directly to the current layer node.
                release event.key to global.layer
            }

        }
    }

    node normal {
        # ... Imagine state and handlers here ...
    }

    node nav {
        # ... Imagine state and handlers here ...
    }

    node sym {
        # ... Imagine state and handlers here ...
    }

    edges {
        input >> router

        # The router node dynamically routes events to the global.layer node.
        normal >> output
        nav >> output
        sym >> output
    }
}
```

#### Multiple Output Ports

Another way to implement layers is to use node references. For example:

```
graph main {
    config {
        nav_key = "left alt"
        sym_key = "right alt"
    }

    global {
        layer = "normal"
    }

    node router {
        on press(event) {
            if global.layer == "normal" {
                match event.key {
                    case config.nav_key { global.layer = "nav" }
                    case config.sym_key { global.layer = "sym" }
                    case * { press event.key to normal }
                }
            } else if global.layer == "nav" {
                press event.key to nav
            } else if global.layer == "sym" {
                press event.key to sym
            }
        }

        on release(event) {
            if global.layer == "nav" and event.key == config.nav_key {
                global.layer = "normal"
            } else if global.layer == "sym" and event.key == config.sym_key {
                global.layer = "normal"
            } else {
                # Send the event to the right output port.
                match global.layer {
                    case "normal" { release event.key to normal }
                    case "nav" { release event.key to nav }
                    case "sym" { release event.key to sym }
                }
            }

        }
    }

    node normal {
        # ... Imagine state and handlers here ...
    }

    node nav {
        # ... Imagine state and handlers here ...
    }

    node sym {
        # ... Imagine state and handlers here ...
    }

    edges {
        input >> router

        router.normal >> normal >> output
        router.nav >> nav >> output
        router.sym >> sym >> output
    }
}
```

## Examples

### ComboComposerV2

This node allows the user to tap one or more modifiers, which will then all be
applied to the next non-modifier key.

It is slightly different from the `ComboComposerV1` example above, which uses
a `tick` event handler to hold down the combo keys for some duration.

```
node ComboComposerV2 {
    state {
        mode = "idle"
        keys = {}
    }

    on press(event) {
        if event.key == "compose-combo" {
            if state.mode == "idle" {
                state.mode == "starting"
                state.keys = {}
            } else if state.mode == "recording" {
                state.mode = "pressing"
                press_combo()
            }
        } else if state.mode == "idle" {
            press event.key
        } else mode == "starting" or mode == "recording" {
            state.keys << event.key
        }
    }

    on release(event) {
        if event.key == "compose-combo" {
            if state.mode == "starting" {
                state.mode = "recording"
            } else if state.mode == "pressing" {
                release_combo()
                state.mode = "idle"
                state.keys = {}
            }
        } else if state.mode == "idle" {
            release event.key
        }
    }

    function press_combo() {
        for key in state.keys if is_modifier(key) { press key }
        for key in state.keys if not is_modifier(key) { press key }
    }

    function release_combo() {
        for key in state.keys if not is_modifier(key) { release key }
        for key in state.keys if is_modifier(key) { release key }
    }
}
```

### Debouncer

This node filters out repeat key events that occur too close together.

```
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
        if state.is_pressed.contains(event.key) {
            state.is_pressed.remove(event.key)
            release event.key
        }
    }
}
```

### Combo Engine

```
# Each combo is represented as a set of input keys and a final output key.
class Combo {
    input: Set<Key>
    output: Key
}


node ComboEngine {
    config {
        combos = [
            Combo(input = {"j", "k"}, output = "escape"),
            Combo(input = {"t", "y"}, output = "="),
        ]

        # All keys must be pressed within this much time of each other.
        press_window = 15 * ms

        # All keys must be released within this much time of each other.
        release_window = 15 * ms

        # No keys must be held for longer than this duration.
        max_hold = 25 * ms
    }

    state {
        # Track which keys are currently pressed and when
        pressed: Map<Key, Time> = {:}

        # Buffer of pending events that might be part of a combo
        buffer = []

        # Time when first key in potential combo was pressed
        combo_start_time = 0
    }

    on press(event) {
        if is_combo_key(event.key) {
            # Start or continue a potential combo
            if state.pressed.count() == 0 {
                state.combo_start_time = event.time
            }

            state.pressed[event.key] = event.time
            state.buffer << event
            return
        }

        # Non-combo key pressed - flush any pending combo
        flush_buffer()
        press event.key
    }

    on release(event) {
        if is_combo_key(event.key) and state.pressed.contains(event.key) {
            state.buffer << event
            state.pressed.remove(event.key)

            # Check if all keys released - might be a complete combo
            if state.pressed.count() == 0 {
                check_for_combo()
            }
            return
        }

        # Non-combo key or not in pressed set
        flush_buffer()
        release event.key
    }

    on tick(event) {
        if state.pressed.count() > 0 {
            # Check if combo has timed out
            if event.time - state.combo_start_time > config.max_hold {
                flush_buffer()
            }
        }
    }

    function is_combo_key(key: Key): bool {
        for combo in config.combos {
            if combo.input.contains(key) {
                return true
            }
        }
        return false
    }

    function check_for_combo() {
        # Extract the keys that were pressed
        pressed_keys = {}
        first_press_time = 0
        last_press_time = 0
        first_release_time = 0
        last_release_time = 0

        for event in state.buffer {
            if event.type == "press" {
                pressed_keys << event.key
                if first_press_time == 0 {
                    first_press_time = event.time
                }
                last_press_time = event.time
            } else if event.type == "release" {
                if first_release_time == 0 {
                    first_release_time = event.time
                }
                last_release_time = event.time
            }
        }

        # Check timing windows
        press_spread = last_press_time - first_press_time
        release_spread = last_release_time - first_release_time
        hold_duration = first_release_time - last_press_time

        if press_spread <= config.press_window and
           release_spread <= config.release_window and
           hold_duration <= config.max_hold {

            # Check if pressed keys match any combo
            for combo in config.combos {
                if pressed_keys == combo.input {
                    # Combo detected! Emit the output
                    press combo.output
                    release combo.output
                    clear_state()
                    return
                }
            }
        }

        # Not a valid combo - replay the buffered events
        flush_buffer()
    }

    function flush_buffer() {
        # Replay all buffered events as-is
        for event in state.buffer {
            if event.type == "press" {
                press event.key
            } else if event.type == "release" {
                release event.key
            }
        }
        clear_state()
    }

    function clear_state() {
        state.buffer = []
        state.pressed = {:}
        state.combo_start_time = 0
    }
}
```

### Chording Engine

```
# Each chord is represented as a set of input keys and a list of output keys.
class Chord {
    input: Set<Key>
    output: List<Key>
}


node ChordingEngine {
    config {
        chords = [
            Chord(input = {"d", "e", "f"}, output = ["d", "e", "f"]),
            Chord(input = {"c", "l", "s"}, output = ["c", "l", "a", "s", "s"]),
        ]

        # All keys must be released within this much time of each other.
        release_window = 20 * ms
    }

    state {
        # Track currently pressed keys that might be part of a chord
        pressed_keys: Set<Key> = {}

        # Buffer to track release events
        release_buffer = []

        # Time of first release in current sequence
        first_release_time = 0

        # Keys we've already processed (to avoid double-processing)
        processed: Set<Key> = {}
    }

    on press(event) {
        if is_chord_key(event.key) {
            state.pressed_keys << event.key
            # Don't emit anything yet - wait to see if it's a chord
            return
        }

        # Non-chord key - emit normally
        press event.key
    }

    on release(event) {
        if is_chord_key(event.key) and state.pressed_keys.contains(event.key) {
            # Start or continue tracking releases
            if state.release_buffer.size() == 0 {
                state.first_release_time = event.time
            }

            state.release_buffer << event
            state.pressed_keys.remove(event.key)

            # Check if this could be a chord
            check_for_chord()
            return
        }

        # Non-chord key or not pressed - emit normally
        release event.key
    }

    on tick(event) {
        # Check if we have a partial release that's timed out
        if state.release_buffer.size() > 0 {
            if event.time - state.first_release_time > config.release_window {
                # Timeout - flush any pending releases
                flush_releases()
            }
        }
    }

    function is_chord_key(key: Key): bool {
        for chord in config.chords {
            if chord.input.contains(key) {
                return true
            }
        }
        return false
    }

    function check_for_chord() {
        # Build set of all released keys so far
        released_keys = {}
        for event in state.release_buffer {
            released_keys << event.key
        }

        # Check if released keys match any chord exactly
        for chord in config.chords {
            if released_keys == chord.input {
                # Perfect match! Check timing
                last_release_time = state.release_buffer[-1].time

                if last_release_time - state.first_release_time <= config.release_window {
                    # Valid chord! Emit the output sequence
                    emit_chord_output(chord)
                    clear_state()
                    return
                }
            }
        }

        # Check if we could still be building toward a chord
        could_be_chord = false
        for chord in config.chords {
            # Released keys must be subset of chord input
            if released_keys.is_subset_of(chord.input) {
                # And we must still have the remaining keys pressed
                remaining = chord.input - released_keys
                if remaining.is_subset_of(state.pressed_keys) {
                    could_be_chord = true
                    break
                }
            }
        }

        if not could_be_chord {
            # No possible chord - flush releases
            flush_releases()
        }
        # Otherwise, keep waiting for more releases
    }

    function emit_chord_output(chord: Chord) {
        # Emit the chord's output sequence
        for key in chord.output {
            press key
            release key
        }

        # Mark all chord keys as processed
        for key in chord.input {
            state.processed << key
        }
    }

    function flush_releases() {
        # Emit all buffered releases as individual keys
        for event in state.release_buffer {
            # Only emit if not already processed as part of a chord
            if not state.processed.contains(event.key) {
                press event.key
                release event.key
            }
        }
        clear_state()
    }

    function clear_state() {
        state.release_buffer = []
        state.first_release_time = 0
        state.processed = {}
        # Note: Don't clear pressed_keys - some might still be held
    }
}
```

## Leader Key

```
class LeaderSequence {
    input: List<Key>
    output: List<Key>
}

class LeaderKey {
    config {
        leader_key = "CapsLock"

        sequences = [
            Chord(input = ["a", "m"], output = ["&"]),
            Chord(input = ["e", "q"], output = ["="]),
            Chord(input = ["e", "e"], output = ["=", "="]),
            Chord(input = ["n", "e"], output = ["!", "="]),
        ]

        # Initial grace period.
        initial_timeout = 2 * seconds

        # Subsequent time out after each key press.
        subsequent_timeout = 500 * ms
    }

    state {
        mode = "follower"
        buffer = []
    }

    on press(event) {
        if state.mode == "leader" {
            state.buffer << event
            check-buffer()
        } if event.key == config.leader_key {
            state.mode = "leader"
            state.buffer = []
        } else {
            press event.key to output
        }
    }

    on release(event) {
        if state.mode == "leader" {
            state.buffer << event
            check-buffer()
        } else {
            release event.key to output
        }
    }

    function check-buffer() {
        # TODO: Compare the buffer to each LeaderSequence. If you find a match,
        # then emit the output keys. If you find a break, then reset the state.
        # Emit an error key on a special error port, so that a downstream node
        # may play a sound or flash a pixel or display an error.
    }
}
```

## Compilation Target

The DSL compiles to C code that integrates with QMK/ZMK:

- **Input integration**: Hooks into QMK's `process_record_user()`, or ZMK's
behavior system, or hid-remapper's `set_input_state/process_mapping` functions.
- **Output integration**: Calls QMK's `register_code()/unregister_code()` or
ZMK's HID functions.
- **State management**: Generates C structs and functions for each node.
- **Event routing**: Generates function calls based on connection graph
- **Reference counting**: Automatically increments and decrements reference
counts, freeing objects when their count reaches zero.

## Potential Advantages Over QMK/ZMK

1. **Unified abstraction**: Everything is nodes processing event streams.
2. **Natural composability**: Complex behaviors emerge from simple node combinations.
3. **Clear mental model**: Stream processing vs configuration of special cases.
4. **Easy extensibility**: New behaviors are just new nodes.
5. **Expressive power**: Can implement behaviors that would be very difficult in
QMK (like modifier composer).
6. **Testability**: Nodes can be unit tested independently.

## Implementation Notes

- Compiler should generate efficient C code suitable for microcontroller constraints.
- State should be allocated statically where possible.
- Event routing should compile to direct function calls.
- Built-in functions like is_modifier() should be provided by runtime library.
Support for debugging/tracing could be added via compilation flags
- For memory management, the system uses automatic reference counting.
- Be careful not to have cycles!

## Questions

- Are there glaring flaws or fundamental problems with this design?
- Does this DSL solve anything, or does it just push the complexity around?
- Could this DSL be used to model a very complex keyboard, while still being
readable and understandable?
- Does this DSL need additional abstractions to help manage complexity?
- Does this DSL have too many abstractions?

### Design Questions

- Why does it need to be `event.action(...)` instead of just `event(...)`?
- Should the `emit` keyword be required for `event.action(event.key)`?
- If not, should the `emit` keyword be removed from the grammar?
- Are there too many ways to implement layers?
- Should support for first-class nodes and graphs be removed?

## Todo

- Finish examples.
- Provide more examples.
- Make exmamples of template functions.
