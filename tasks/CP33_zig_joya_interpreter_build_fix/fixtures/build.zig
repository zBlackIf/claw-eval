const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // BUG: .root_source_file is the old Zig 0.13 API.
    // Zig 0.16.0 uses .root_module with .root_source_file as a sub-field
    const exe = b.addExecutable(.{
        .name = "joya",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());

    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    const run_step = b.step("run", "Run the interpreter");
    run_step.dependOn(&run_cmd.step);
}
