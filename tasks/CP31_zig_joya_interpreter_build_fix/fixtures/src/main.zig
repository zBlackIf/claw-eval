const std = @import("std");
const Lexer = @import("lexer.zig").Lexer;
const Parser = @import("parser.zig").Parser;
const Interpreter = @import("interpreter.zig").Interpreter;

pub fn main() !void {
    const allocator = std.heap.page_allocator;
    var args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len < 2) {
        std.debug.print("Usage: joya <script.joya>\n", .{});
        return;
    }

    const filename = args[1];
    const source = try std.fs.cwd().readFileAlloc(allocator, filename, 1024 * 1024);
    defer allocator.free(source);

    var lexer = Lexer.init(source);
    const tokens = try lexer.tokenize(allocator);

    var parser = Parser.init(tokens, allocator);
    const ast = try parser.parse();

    var interpreter = Interpreter.init(allocator);
    try interpreter.execute(ast);
}
