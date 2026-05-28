# Zig 0.16.0 Build API Migration Notes

## Key Changes from 0.13 -> 0.16

### 1. root_module replaces root_source_file
Old (0.13):
```zig
const exe = b.addExecutable(.{
    .name = "app",
    .root_source_file = b.path("src/main.zig"),
    .target = target,
    .optimize = optimize,
});
```

New (0.16):
```zig
const exe = b.addExecutable(.{
    .name = "app",
    .root_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    }),
});
```

### 2. Unused variables
- 0.16 enforces `_ = variable;` for intentionally unused captures
- Unused function parameters: use `_` prefix

### 3. Import changes
- `@import("builtin")` available in build.zig
