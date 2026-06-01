const std = @import("std");
const Token = @import("lexer.zig").Token;
const TokenType = @import("lexer.zig").TokenType;
const ast = @import("ast.zig");

pub const Parser = struct {
    tokens: []const Token,
    pos: usize,
    allocator: std.mem.Allocator,

    pub fn init(tokens: []const Token, allocator: std.mem.Allocator) Parser {
        return .{ .tokens = tokens, .pos = 0, .allocator = allocator };
    }

    // BUG: unused function parameter 'self'
    pub fn deinit(self: *Parser) void {
        _ = self;
    }

    pub fn parse(self: *Parser) ![]ast.Statement {
        var stmts = std.ArrayList(ast.Statement).init(self.allocator);
        while (self.peek()) |tok| {
            if (tok.type == .eof) break;
            const stmt = try self.parseStatement();
            try stmts.append(stmt);
        }
        return stmts.toOwnedSlice();
    }

    fn parseStatement(self: *Parser) !ast.Statement {
        // BUG: 'tok' should be const, not var
        var tok = self.peek() orelse return error.UnexpectedEof;

        return switch (tok.type) {
            .let_kw => self.parseLetStatement(),
            .print_kw => self.parsePrintStatement(),
            .if_kw => self.parseIfStatement(),
            else => error.UnexpectedToken,
        };
    }

    fn parseLetStatement(self: *Parser) !ast.Statement {
        _ = self.advance(); // consume 'let'
        const name_tok = self.advance() orelse return error.UnexpectedEof;
        _ = self.expect(.equals) orelse return error.ExpectedEquals;
        const expr = try self.parseExpression();
        _ = self.expect(.semicolon);
        return .{ .let_stmt = .{ .name = name_tok.lexeme, .value = expr } };
    }

    fn parsePrintStatement(self: *Parser) !ast.Statement {
        _ = self.advance(); // consume 'print'
        _ = self.expect(.lparen) orelse return error.ExpectedLParen;
        const expr = try self.parseExpression();
        _ = self.expect(.rparen);
        _ = self.expect(.semicolon);
        return .{ .print_stmt = .{ .value = expr } };
    }

    fn parseIfStatement(self: *Parser) !ast.Statement {
        _ = self.advance(); // consume 'if'
        _ = self.expect(.lparen) orelse return error.ExpectedLParen;
        const cond = try self.parseExpression();
        _ = self.expect(.rparen);
        _ = self.expect(.lbrace);
        const then_body = try self.parseBlock();
        var else_body: ?[]ast.Statement = null;
        if (self.peek()) |tok| {
            if (tok.type == .else_kw) {
                _ = self.advance();
                _ = self.expect(.lbrace);
                else_body = try self.parseBlock();
            }
        }
        return .{ .if_stmt = .{ .condition = cond, .then_body = then_body, .else_body = else_body } };
    }

    fn parseBlock(self: *Parser) ![]ast.Statement {
        var stmts = std.ArrayList(ast.Statement).init(self.allocator);
        while (self.peek()) |tok| {
            if (tok.type == .rbrace) {
                _ = self.advance();
                break;
            }
            if (tok.type == .eof) break;
            try stmts.append(try self.parseStatement());
        }
        return stmts.toOwnedSlice();
    }

    fn parseExpression(self: *Parser) !ast.Expression {
        var left = try self.parsePrimary();
        while (self.peek()) |tok| {
            if (tok.type == .plus or tok.type == .minus or
                tok.type == .star or tok.type == .slash or
                tok.type == .gt or tok.type == .lt)
            {
                const op = self.advance().?;
                const right = try self.parsePrimary();
                left = .{ .binary = .{
                    .left = &left,
                    .op = op.type,
                    .right = &right,
                } };
            } else {
                break;
            }
        }
        return left;
    }

    fn parsePrimary(self: *Parser) !ast.Expression {
        const tok = self.advance() orelse return error.UnexpectedEof;
        return switch (tok.type) {
            .number => .{ .number_lit = std.fmt.parseInt(i64, tok.lexeme, 10) catch 0 },
            .string_lit => .{ .string_lit = tok.lexeme },
            .ident => .{ .identifier = tok.lexeme },
            .lparen => blk: {
                const expr = try self.parseExpression();
                _ = self.expect(.rparen);
                break :blk expr;
            },
            else => error.UnexpectedToken,
        };
    }

    fn peek(self: *const Parser) ?Token {
        if (self.pos < self.tokens.len) return self.tokens[self.pos];
        return null;
    }

    fn advance(self: *Parser) ?Token {
        if (self.pos < self.tokens.len) {
            const tok = self.tokens[self.pos];
            self.pos += 1;
            return tok;
        }
        return null;
    }

    fn expect(self: *Parser, expected: TokenType) ?Token {
        if (self.peek()) |tok| {
            if (tok.type == expected) return self.advance();
        }
        return null;
    }
};
