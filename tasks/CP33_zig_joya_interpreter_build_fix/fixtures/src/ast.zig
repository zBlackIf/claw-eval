const TokenType = @import("lexer.zig").TokenType;

pub const Expression = union(enum) {
    number_lit: i64,
    string_lit: []const u8,
    identifier: []const u8,
    binary: BinaryExpr,
};

pub const BinaryExpr = struct {
    left: *const Expression,
    op: TokenType,
    right: *const Expression,
};

pub const Statement = union(enum) {
    let_stmt: LetStatement,
    print_stmt: PrintStatement,
    if_stmt: IfStatement,
};

pub const LetStatement = struct { name: []const u8, value: Expression };
pub const PrintStatement = struct { value: Expression };
pub const IfStatement = struct { condition: Expression, then_body: []Statement, else_body: ?[]Statement };
