"""Docker container lifecycle management for sandbox execution.

New architecture: the agent loop stays on the host, the container only runs
a lightweight sandbox HTTP server.  The host-side dispatcher sends tool calls
to the container over HTTP.

Container lifecycle:
  1. start_container() — launch container, wait for /health
  2. (host runs agent loop, dispatching sandbox_* tools via HTTP)
  3. stop_container() — destroy container
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import secrets

from ..config import SandboxConfig
from .sandbox_errors import SandboxInfraError


@dataclass
class ContainerHandle:
    """Reference to a running agent container."""

    container: Any  # docker Container object
    host_port: int  # sandbox service's mapped host port
    run_id: str
    task_id: str
    token: str
    sandbox_url: str  # "http://127.0.0.1:{host_port}"


class SandboxRunner:
    """Manages Docker containers for sandboxed agent evaluation."""

    def __init__(
        self,
        sandbox_config: SandboxConfig,
        *,
        image: str | None = None,
    ) -> None:
        try:
            import docker  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "docker package is required for sandbox mode. "
                "Install with: pip install 'claw-eval[sandbox]'"
            ) from None

        self._config = sandbox_config
        self._image = image or sandbox_config.image

        kwargs: dict[str, Any] = {}
        if sandbox_config.docker_host:
            kwargs["base_url"] = sandbox_config.docker_host
        else:
            context_host = self._active_docker_context_host()
            if context_host:
                kwargs["base_url"] = context_host
        if "base_url" in kwargs:
            self._docker = docker.DockerClient(**kwargs)
        else:
            self._docker = docker.from_env()

    @staticmethod
    def _active_docker_context_host() -> str | None:
        """Return the Docker endpoint for the active CLI context when useful.

        The Python Docker SDK reads DOCKER_HOST but does not automatically
        honor `docker context use colima`. Local development often relies on
        that context, so infer the endpoint when DOCKER_HOST is absent.
        """
        import json
        import os
        import subprocess

        if os.environ.get("DOCKER_HOST"):
            return None
        try:
            proc = subprocess.run(
                ["docker", "context", "inspect"],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            return None
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        try:
            contexts = json.loads(proc.stdout)
            host = (
                contexts[0]
                .get("Endpoints", {})
                .get("docker", {})
                .get("Host")
            )
        except Exception:
            return None
        if isinstance(host, str) and host and host != "unix:///var/run/docker.sock":
            return host
        return None

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _proxy_env() -> dict[str, str]:
        """Collect proxy environment variables from the host."""
        import os

        env = {}
        for key in (
            "http_proxy", "https_proxy", "no_proxy",
            "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        ):
            val = os.environ.get(key)
            if val:
                env[key] = val
        return env

    @staticmethod
    def _token_sha256(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def identity_headers(handle: ContainerHandle) -> dict[str, str]:
        return {
            "X-Claw-Sandbox-Run-Id": handle.run_id,
            "X-Claw-Sandbox-Task-Id": handle.task_id,
            "X-Claw-Sandbox-Token": handle.token,
        }

    @staticmethod
    def identity_payload(handle: ContainerHandle) -> dict[str, str]:
        return {
            "run_id": handle.run_id,
            "task_id": handle.task_id,
            "token": handle.token,
        }

    @staticmethod
    def _public_identity(handle: ContainerHandle) -> dict[str, str]:
        return {
            "run_id": handle.run_id,
            "task_id": handle.task_id,
            "token_sha256": SandboxRunner._token_sha256(handle.token),
        }

    @staticmethod
    def _container_diagnostics(container: Any) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {
            "container_id": getattr(container, "short_id", None) or getattr(container, "id", None),
            "container_name": getattr(container, "name", None),
        }
        try:
            container.reload()
        except Exception as exc:
            diagnostics["container_inspect_error"] = str(exc)

        attrs = getattr(container, "attrs", None) or {}
        state = attrs.get("State", {}) if isinstance(attrs, dict) else {}
        diagnostics["container_status"] = state.get("Status") or getattr(container, "status", None)
        diagnostics["exit_code"] = state.get("ExitCode")
        diagnostics["oom_killed"] = state.get("OOMKilled")
        diagnostics["state_error"] = state.get("Error")
        return diagnostics

    @staticmethod
    def _format_diagnostics(fields: dict[str, Any]) -> str:
        return " ".join(
            f"{key}={value}"
            for key, value in fields.items()
            if value is not None
        )

    @staticmethod
    def _handle_diagnostics(handle: ContainerHandle) -> dict[str, Any]:
        diagnostics = {
            "run_id": handle.run_id,
            "task_id": handle.task_id,
            "host_port": handle.host_port,
            "sandbox_url": handle.sandbox_url,
            "identity": SandboxRunner._public_identity(handle),
        }
        diagnostics.update(SandboxRunner._container_diagnostics(handle.container))
        return diagnostics

    def describe_handle(self, handle: ContainerHandle) -> dict[str, Any]:
        """Return current sandbox/container diagnostics for result metadata."""
        diagnostics = self._handle_diagnostics(handle)
        try:
            import httpx

            with httpx.Client(timeout=2.0, headers=self.identity_headers(handle)) as client:
                health = client.get(f"{handle.sandbox_url}/health")
                diagnostics["health_status"] = health.status_code
                diagnostics["health"] = health.json()
                diag = client.get(f"{handle.sandbox_url}/diagnostics")
                diagnostics["server_diagnostics_status"] = diag.status_code
                diagnostics["server_diagnostics"] = diag.json()
        except Exception as exc:
            diagnostics["server_diagnostics_error"] = str(exc)
        try:
            raw_logs = handle.container.logs(tail=200)
            if isinstance(raw_logs, bytes):
                raw_logs = raw_logs.decode("utf-8", errors="replace")
            tail_bytes = max(1024, int(getattr(self._config, "log_tail_bytes", 65536) or 65536))
            diagnostics["docker_log_tail"] = str(raw_logs)[-tail_bytes:]
        except Exception as exc:
            diagnostics["docker_log_error"] = str(exc)
        return diagnostics

    @staticmethod
    def _log_stage(
        stage: str,
        *,
        run_id: str | None = None,
        handle: ContainerHandle | None = None,
        container: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        fields: dict[str, Any] = {"stage": stage, "run_id": run_id}
        if handle is not None:
            fields.update(SandboxRunner._handle_diagnostics(handle))
        elif container is not None:
            fields.update(SandboxRunner._container_diagnostics(container))
        if exc is not None:
            fields["exc_type"] = type(exc).__name__
            fields["exc"] = str(exc)
        prefix = "[sandbox-stage-error]" if exc is not None else "[sandbox-stage]"
        print(f"{prefix} {SandboxRunner._format_diagnostics(fields)}")

    def start_container(self, *, run_id: str, task_id: str | None = None) -> ContainerHandle:
        """Launch an agent container and wait for the sandbox service.

        Returns a *ContainerHandle* with the sandbox HTTP URL that the
        host-side dispatcher should send ``sandbox_*`` tool calls to.
        """
        container = None
        handle = None
        resolved_task_id = task_id or run_id
        token = secrets.token_urlsafe(32)
        self._log_stage("start_container", run_id=run_id)
        try:
            env = self._proxy_env()
            env.update({
                "CLAW_EVAL_SANDBOX_RUN_ID": run_id,
                "CLAW_EVAL_SANDBOX_TASK_ID": resolved_task_id,
                "CLAW_EVAL_SANDBOX_TOKEN": token,
            })
            container = self._docker.containers.run(
                image=self._image,
                detach=True,
                name=f"claw-agent-{run_id}",
                mem_limit=self._config.memory_limit,
                nano_cpus=int(self._config.cpu_limit * 1e9),
                ports={f"{self._config.sandbox_port}/tcp": ("127.0.0.1", None)},  # IPv4-only, avoids IPv6 port collision
                labels={
                    "app": "claw-eval",
                    "role": "agent",
                    "run_id": run_id,
                    "task_id": resolved_task_id,
                },
                environment=env,
            )

            host_port = self._get_mapped_port(container)
            sandbox_url = f"http://127.0.0.1:{host_port}"
            handle = ContainerHandle(
                container=container,
                host_port=host_port,
                run_id=run_id,
                task_id=resolved_task_id,
                token=token,
                sandbox_url=sandbox_url,
            )
            self._log_stage("wait_healthy", handle=handle)
            self._wait_healthy(f"{sandbox_url}/health")
        except Exception as exc:
            self._log_stage("start_container", run_id=run_id, handle=handle, container=container, exc=exc)
            raise

        print(f"[sandbox] Container claw-agent-{run_id} started at {sandbox_url}")
        self._log_stage("ready", handle=handle)
        return handle

    def stop_container(self, handle: ContainerHandle, *, preserve: bool = False) -> None:
        """Stop and remove a running agent container."""
        self._log_stage("stop_container", handle=handle)
        if preserve:
            print(f"[sandbox] Preserving container claw-agent-{handle.run_id} for diagnostics")
            return
        try:
            handle.container.remove(force=True)
            print(f"[sandbox] Container claw-agent-{handle.run_id} removed")
        except Exception as exc:
            self._log_stage("stop_container", handle=handle, exc=exc)
            print(f"[sandbox] Warning: failed to remove container: {exc}")

    def cleanup_all(self) -> int:
        """Remove all claw-eval agent containers (e.g. after a crash)."""
        containers = self._docker.containers.list(
            all=True, filters={"label": ["app=claw-eval"]}
        )
        for c in containers:
            c.remove(force=True)
        return len(containers)

    # ------------------------------------------------------------------
    # File injection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_infra_response(status_code: int, body: Any) -> bool:
        if status_code >= 500:
            return True
        return isinstance(body, dict) and (
            body.get("infra_error") is True
            or str(body.get("error_code") or "").startswith("sandbox_")
        )

    @staticmethod
    def _raise_for_infra_response(
        *,
        label: str,
        rel_path: str,
        status_code: int,
        body: Any,
        handle: ContainerHandle,
    ) -> None:
        if not SandboxRunner._is_infra_response(status_code, body):
            return
        if isinstance(body, dict):
            error_code = str(body.get("error_code") or "sandbox_transport")
            message = str(body.get("message") or body.get("error") or body)
            diagnostics = dict(body.get("diagnostics") or {})
        else:
            error_code = "sandbox_transport"
            message = str(body)
            diagnostics = {}
        diagnostics.update({
            "label": label,
            "rel_path": rel_path,
            "status_code": status_code,
            "sandbox_url": handle.sandbox_url,
        })
        raise SandboxInfraError(error_code, message, diagnostics=diagnostics)

    @staticmethod
    def _required_roots(file_list: list[str]) -> list[str]:
        roots: set[str] = set()
        for rel_path in file_list:
            parts = Path(rel_path).parts
            if not parts:
                continue
            if parts[0] == "fixtures" and len(parts) >= 2:
                roots.add(f"/workspace/fixtures/{parts[1]}")
            elif len(parts) >= 1:
                roots.add(f"/workspace/{parts[0]}")
        return sorted(roots)

    @staticmethod
    def _bootstrap_identity(handle: ContainerHandle, required_roots: list[str], injected: int) -> None:
        import httpx

        try:
            resp = httpx.post(
                f"{handle.sandbox_url}/identity/bootstrap",
                json={"required_roots": required_roots, "injected_files": injected},
                headers=SandboxRunner.identity_headers(handle),
                timeout=30.0,
            )
            try:
                body = resp.json()
            except Exception:
                body = {"error": resp.text[:1000]}
            SandboxRunner._raise_for_infra_response(
                label="identity-bootstrap",
                rel_path="<identity>",
                status_code=resp.status_code,
                body=body,
                handle=handle,
            )
            if resp.status_code >= 400:
                raise SandboxInfraError(
                    "sandbox_transport",
                    f"identity bootstrap failed: {resp.status_code} {str(body)[:500]}",
                    diagnostics={"status_code": resp.status_code, "body": body},
                )
        except SandboxInfraError:
            raise
        except Exception as exc:
            raise SandboxInfraError(
                "sandbox_transport",
                f"identity bootstrap failed: {exc}",
                diagnostics={"sandbox_url": handle.sandbox_url, "exc_type": type(exc).__name__},
            ) from exc

    @staticmethod
    def _inject_file_list(
        handle: ContainerHandle,
        file_list: list[str],
        root: "Path",
        *,
        label: str = "inject",
    ) -> int:
        """Push a list of files into a running container.

        Shared implementation for both :meth:`inject_files` (pre-loop) and
        :meth:`inject_grader_files` (post-loop).

        Returns the number of files successfully injected.
        """
        import base64
        import mimetypes
        from pathlib import Path

        import httpx

        if not file_list:
            return 0

        client = httpx.Client(timeout=30.0, headers=SandboxRunner.identity_headers(handle))
        injected = 0

        _TEXT_MIMES = {
            "text/plain", "text/csv", "text/markdown", "text/html",
            "text/xml", "application/json", "application/xml",
            "application/yaml", "application/x-yaml", "application/javascript",
            "application/sql", "application/x-sql", "application/x-sh",
            "application/x-shellscript",
        }
        _TEXT_EXTENSIONS = {
            ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".ndjson",
            ".yaml", ".yml", ".xml", ".html", ".htm", ".css", ".scss", ".sass",
            ".less", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte",
            ".py", ".pyi", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
            ".cfg", ".conf", ".ini", ".toml", ".env", ".properties", ".log", ".sql",
            ".r", ".rmd", ".java", ".kt", ".kts", ".scala", ".sc", ".groovy",
            ".gradle", ".c", ".cc", ".cxx", ".cpp", ".h", ".hh", ".hpp", ".hxx",
            ".cs", ".php", ".go", ".rs", ".dart", ".swift", ".m", ".mm", ".lua",
            ".pl", ".pm", ".rb", ".ex", ".exs", ".erl", ".hrl", ".clj", ".cljs",
            ".edn", ".zig", ".gd", ".proto", ".lmp", ".dockerfile", ".gitignore",
            ".dockerignore", ".npmrc", ".yarnrc", ".editorconfig", ".lock", ".service",
            ".timer",
        }
        _TEXT_FILENAMES = {
            "dockerfile",
            "makefile",
            "rakefile",
            "gemfile",
            "podfile",
            "cmakelists.txt",
        }

        def _looks_like_utf8_text(path: Path, sample_size: int = 8192) -> bool:
            try:
                with path.open("rb") as fh:
                    sample = fh.read(sample_size)
            except OSError:
                return False
            if not sample:
                return True
            if b"\x00" in sample:
                return False
            try:
                sample.decode("utf-8")
            except UnicodeDecodeError:
                return False
            control_bytes = sum(
                1 for byte in sample
                if byte < 32 and byte not in (8, 9, 10, 12, 13)
            )
            return (control_bytes / len(sample)) <= 0.05

        def _is_text_file(path: Path, mime: str | None, ext: str) -> bool:
            if ext in _TEXT_EXTENSIONS or path.name.lower() in _TEXT_FILENAMES:
                return True
            if mime in _TEXT_MIMES or (mime is not None and mime.startswith("text/")):
                return True
            if mime is None:
                return _looks_like_utf8_text(path)
            return False

        # Project root for cross-task fixture references (e.g. "tasks/T14/fixtures/...")
        # Walk up from the resolved task dir to find the directory containing "tasks/"
        project_root = root.resolve().parent  # fallback
        _pr = root.resolve()
        while _pr.parent != _pr:
            if (_pr / "tasks").is_dir():
                project_root = _pr
                break
            _pr = _pr.parent

        SandboxRunner._log_stage(label, handle=handle)
        try:
            for rel_path in file_list:
                src = root / rel_path
                if not src.exists():
                    # Cross-task reference: try resolving from project root
                    alt = project_root / rel_path
                    if alt.exists():
                        src = alt
                    else:
                        print(f"[sandbox] {label}: skipping {rel_path} (not found at {src} or {alt})")
                        continue

                container_path = f"/workspace/{rel_path}"
                mime, _ = mimetypes.guess_type(str(src))
                ext = src.suffix.lower()
                is_text = _is_text_file(src, mime, ext)

                if is_text:
                    content = src.read_text(encoding="utf-8", errors="replace")
                    resp = client.post(
                        f"{handle.sandbox_url}/write",
                        json={"path": container_path, "content": content},
                    )
                else:
                    b64 = base64.b64encode(src.read_bytes()).decode("ascii")
                    resp = client.post(
                        f"{handle.sandbox_url}/write_b64",
                        json={"path": container_path, "content_b64": b64},
                    )

                try:
                    body = resp.json()
                except Exception:
                    body = {"error": resp.text[:1000]}
                SandboxRunner._raise_for_infra_response(
                    label=label,
                    rel_path=rel_path,
                    status_code=resp.status_code,
                    body=body,
                    handle=handle,
                )

                if resp.status_code < 400:
                    injected += 1
                else:
                    print(f"[sandbox] {label}: failed {rel_path} — {resp.status_code} {resp.text[:100]}")
        except Exception as exc:
            SandboxRunner._log_stage(label, handle=handle, exc=exc)
            raise
        finally:
            client.close()

        if injected:
            print(f"[sandbox] {label}: {injected}/{len(file_list)} files into container")
        return injected

    @staticmethod
    def _resolve_task_root(task, task_dir: str | None) -> "Path":
        """Resolve the root directory for task-relative file paths."""
        from pathlib import Path

        if task_dir:
            return Path(task_dir)
        if getattr(task, "task_file", None):
            return Path(task.task_file).parent
        return Path.cwd()

    @staticmethod
    def inject_files(
        handle: ContainerHandle,
        task,
        *,
        task_dir: str | None = None,
    ) -> int:
        """Push task-declared files into a running container via its /write endpoint.

        Which files to inject is determined by (in priority order):
        1. ``task.sandbox_files`` — explicit list in task.yaml
        2. Fallback: ``task.environment.fixtures`` — the fixture manifest

        Paths are relative to *task_dir* (the directory containing task.yaml).
        Inside the container they land under ``/workspace/<relative_path>``.

        Binary files (images, PDFs, etc.) are base64-encoded for transport
        and decoded by a dedicated ``/write_b64`` endpoint.  Text files go
        through the existing ``/write`` endpoint.

        Returns the number of files successfully injected.
        """
        file_list: list[str] = list(task.sandbox_files) if task.sandbox_files else []
        if not file_list:
            file_list = list(getattr(task.environment, "fixtures", []))
        if not file_list:
            return 0

        root = SandboxRunner._resolve_task_root(task, task_dir)
        injected = SandboxRunner._inject_file_list(handle, file_list, root, label="inject")
        SandboxRunner._bootstrap_identity(handle, SandboxRunner._required_roots(file_list), injected)
        return injected

    @staticmethod
    def inject_grader_files(
        handle: ContainerHandle,
        task,
        *,
        task_dir: str | None = None,
    ) -> int:
        """Push grader-only files into container AFTER the agent loop.

        These files (e.g., verify scripts with embedded answers) must not
        be visible to the agent during its run.  They are injected just
        before ``_collect_env_snapshot`` runs.

        Returns the number of files successfully injected.
        """
        file_list: list[str] = list(task.sandbox_grader_files) if getattr(task, "sandbox_grader_files", None) else []
        if not file_list:
            return 0

        root = SandboxRunner._resolve_task_root(task, task_dir)
        return SandboxRunner._inject_file_list(handle, file_list, root, label="grader-inject")

    # ------------------------------------------------------------------
    # Image management
    # ------------------------------------------------------------------

    def build_image(
        self,
        context_path: str = ".",
        *,
        dockerfile: str = "Dockerfile.agent",
    ) -> str:
        """Build the agent container image.

        Args:
            context_path: Docker build context directory.
            dockerfile: Dockerfile name relative to context_path.
        """
        from pathlib import Path

        context_path_abs = str(Path(context_path).resolve())
        print(f"[sandbox] Building image {self._image} from {context_path_abs} (dockerfile={dockerfile}) ...")
        image, logs = self._docker.images.build(
            path=context_path_abs,
            dockerfile=dockerfile,
            tag=self._image,
            rm=True,
        )
        for chunk in logs:
            if "stream" in chunk:
                line = chunk["stream"].rstrip()
                if line:
                    print(f"  {line}")
        print(f"[sandbox] Image built: {image.tags}")
        return self._image

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_mapped_port(self, container) -> int:
        """Resolve the dynamically-assigned host port for the sandbox service."""
        container.reload()
        port_key = f"{self._config.sandbox_port}/tcp"
        bindings = container.ports.get(port_key)
        if not bindings:
            raise RuntimeError(
                f"No port binding found for {port_key}. "
                f"Container ports: {container.ports}"
            )
        return int(bindings[0]["HostPort"])

    def _wait_healthy(self, url: str, timeout: int = 15) -> None:
        """Poll the sandbox /health endpoint until it responds 200."""
        import httpx

        deadline = time.monotonic() + timeout
        last_exc: Exception | None = None
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(url, timeout=2)
                if resp.status_code == 200:
                    return
            except Exception as exc:
                last_exc = exc
            time.sleep(0.3)
        raise RuntimeError(
            f"Sandbox service not ready at {url} after {timeout}s"
            + (f": {last_exc}" if last_exc else "")
        )
