# Joya Language Interpreter

Build a simple interpreter for the Joya scripting language using Zig 0.16.0.

## Language Features

1. Variables: `let x = 42;`
2. Print: `print("hello");` or `print(x);`
3. Arithmetic: `+`, `-`, `*`, `/`
4. String literals: `"hello world"`
5. Comments: `// single line`
6. If/else: `if (x > 10) { print("big"); } else { print("small"); }`

## Architecture

- `lexer.zig`: Tokenizer
- `parser.zig`: AST builder
- `ast.zig`: AST node definitions
- `interpreter.zig`: Tree-walking interpreter
- `main.zig`: Entry point, reads file and runs

## Build

Should compile with `zig build` and run with:
```
zig-out/bin/joya examples/hello.joya
```
