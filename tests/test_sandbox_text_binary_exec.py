import sys
from pathlib import Path

from claw_eval.runner.sandbox_dispatcher import SandboxToolDispatcher
from claw_eval.sandbox import server


def test_read_source_files_as_utf8_when_mimetype_is_unknown_or_non_text(
    monkeypatch, tmp_path
):
    java_file = tmp_path / "Example.java"
    java_file.write_text("package example;\nclass Example {}\n", encoding="utf-8")

    shell_file = tmp_path / "S50nginx"
    shell_file.write_text("#!/bin/sh\necho nginx\n", encoding="utf-8")

    sh_file = tmp_path / "setup.sh"
    sh_file.write_text("#!/bin/sh\necho setup\n", encoding="utf-8")

    def fake_guess_type(path):
        suffix = Path(path).suffix
        if suffix == ".sh":
            return ("application/x-sh", None)
        return (None, None)

    monkeypatch.setattr(server.mimetypes, "guess_type", fake_guess_type)

    for path in (java_file, shell_file, sh_file):
        result = server.read_file(server.FileReadRequest(file_path=str(path)))
        assert result["encoding"] == "utf-8"
        assert "content" in result
        assert not result["content"].startswith("cGFja2FnZ")


def test_exec_preserves_non_utf8_output_without_infra_error():
    command = (
        f"{sys.executable} -c "
        "'import sys; sys.stdout.buffer.write(bytes([0xa5]))'"
    )

    result = server.exec_command(server.ExecRequest(command=command, timeout_seconds=5))

    assert not result.get("infra_error")
    assert result["exit_code"] == 0
    assert "\ufffd" in result["stdout"]


def test_local_shell_exec_preserves_non_utf8_output():
    command = (
        f"{sys.executable} -c "
        "'import sys; sys.stdout.buffer.write(bytes([0xb1]))'"
    )

    result = SandboxToolDispatcher._handle_shell_exec(
        {"command": command, "timeout_seconds": 5}
    )

    assert result["exit_code"] == 0
    assert "\ufffd" in result["stdout"]
