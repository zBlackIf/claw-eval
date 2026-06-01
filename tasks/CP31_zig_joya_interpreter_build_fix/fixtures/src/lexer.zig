const std = @import("std");

pub const TokenType = enum {
    let_kw,
    print_kw,
    if_kw,
    else_kw,
    ident,
    number,
    string_lit,
    lparen,
    rparen,
    lbrace,
    rbrace,
    semicolon,
    equals,
    plus,
    minus,
    star,
    slash,
    gt,
    lt,
    eof,
};

pub const Token = struct {
    type: TokenType,
    lexeme: []const u8,
    line: usize,
};

pub const Lexer = struct {
    source: []const u8,
    pos: usize,
    line: usize,

    pub fn init(source: []const u8) Lexer {
        return .{
            .source = source,
            .pos = 0,
            .line = 1,
        };
    }

    pub fn tokenize(self: *Lexer, allocator: std.mem.Allocator) ![]Token {
        var tokens = std.ArrayList(Token).init(allocator);

        while (self.pos < self.source.len) {
            const c = self.source[self.pos];

            // Skip whitespace
            if (c == ' ' or c == '\t' or c == '\r') {
                self.pos += 1;
                continue;
            }
            if (c == '\n') {
                self.line += 1;
                self.pos += 1;
                continue;
            }

            // Skip comments
            if (c == '/' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == '/') {
                while (self.pos < self.source.len and self.source[self.pos] != '\n') {
                    self.pos += 1;
                }
                continue;
            }

            // Single-char tokens
            const single: ?TokenType = switch (c) {
                '(' => .lparen,
                ')' => .rparen,
                '{' => .lbrace,
                '}' => .rbrace,
                ';' => .semicolon,
                '=' => .equals,
                '+' => .plus,
                '-' => .minus,
                '*' => .star,
                '/' => .slash,
                '>' => .gt,
                '<' => .lt,
                else => null,
            };

            if (single) |tok_type| {
                try tokens.append(.{
                    .type = tok_type,
                    .lexeme = self.source[self.pos .. self.pos + 1],
                    .line = self.line,
                });
                self.pos += 1;
                continue;
            }

            // String literals
            if (c == '"') {
                self.pos += 1;
                const start = self.pos;
                while (self.pos < self.source.len and self.source[self.pos] != '"') {
                    self.pos += 1;
                }
                try tokens.append(.{
                    .type = .string_lit,
                    .lexeme = self.source[start..self.pos],
                    .line = self.line,
                });
                self.pos += 1; // skip closing quote
                continue;
            }

            // Numbers
            if (std.ascii.isDigit(c)) {
                const start = self.pos;
                while (self.pos < self.source.len and std.ascii.isDigit(self.source[self.pos])) {
                    self.pos += 1;
                }
                try tokens.append(.{
                    .type = .number,
                    .lexeme = self.source[start..self.pos],
                    .line = self.line,
                });
                continue;
            }

            // Identifiers and keywords
            if (std.ascii.isAlphabetic(c) or c == '_') {
                // BUG: unused local constant 'start'
                const start = self.pos;
                while (self.pos < self.source.len and
                    (std.ascii.isAlphanumeric(self.source[self.pos]) or self.source[self.pos] == '_'))
                {
                    self.pos += 1;
                }
                const word = self.source[start..self.pos];
                const tok_type: TokenType = if (std.mem.eql(u8, word, "let"))
                    .let_kw
                else if (std.mem.eql(u8, word, "print"))
                    .print_kw
                else if (std.mem.eql(u8, word, "if"))
                    .if_kw
                else if (std.mem.eql(u8, word, "else"))
                    .else_kw
                else
                    .ident;

                try tokens.append(.{
                    .type = tok_type,
                    .lexeme = word,
                    .line = self.line,
                });
                continue;
            }

            // Unknown character
            std.debug.print("Unexpected character '{c}' at line {d}\n", .{ c, self.line });
            self.pos += 1;
        }

        try tokens.append(.{
            .type = .eof,
            .lexeme = "",
            .line = self.line,
        });

        return tokens.toOwnedSlice();
    }
};
