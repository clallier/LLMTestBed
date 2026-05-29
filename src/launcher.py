# ruff: noqa: S104, S603
"""Launcher script for FastAPI backend and Streamlit frontend.

High level role: Detects the host Mac's gateway IP on the VM bridge, configures
the environment, and starts both backend and frontend processes.
"""

import os
import socket
import struct
import subprocess
import sys
import time


def get_gateway_ip() -> str:
    """Retrieves the default gateway IP address from the Linux routing table.

    High level role: Parses /proc/net/route to find the default gateway.

    Returns:
        str: The IPv4 address of the gateway (the host Mac).

    Raises:
        None: All exceptions (e.g., FileNotFoundError when run on macOS or windows)
            are caught and printed as a warning, falling back to return the default bridge IP.

    Examples:
        >>> get_gateway_ip()
        '192.168.64.1'
    """
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as file:
            next(file)  # Skip the header line
            for line in file:
                parts = line.split()
                # Check for the default route where destination is 00000000
                if len(parts) >= 3 and parts[1] == "00000000":
                    gateway_hex = parts[2]
                    return socket.inet_ntoa(struct.pack("<L", int(gateway_hex, 16)))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"[Launcher] Warning: Could not detect gateway IP ({e}). Using default bridge fallback.", flush=True)
    return "192.168.64.1"  # Standard default bridge fallback


def _configure_env(gateway_ip: str) -> None:
    """Configures the OLLAMA_HOST environment variable with the gateway IP.

    High level role: Standardizes system environment configurations.
    It takes the detected gateway IP and sets the OLLAMA_HOST environment variable
    to make sure Ollama client calls map correctly.

    Args:
        gateway_ip (str): The IP address of the gateway bridge.

    Returns:
        None

    Raises:
        None

    Examples:
        >>> _configure_env("192.168.64.1")
    """
    os.environ["OLLAMA_HOST"] = f"http://{gateway_ip}:11434"
    print(f"[Launcher] Detected Host Mac Gateway IP: {gateway_ip}", flush=True)
    print(
        f"[Launcher] Setting OLLAMA_HOST environment variable to: {os.environ['OLLAMA_HOST']}",
        flush=True,
    )


def _start_backend() -> subprocess.Popen:
    """Spawns the FastAPI backend uvicorn subprocess.

    High level role: Asynchronously launches the FastAPI server.
    It constructs the uvicorn command for binding to port 8000 and executes it.

    Args:
        None

    Returns:
        subprocess.Popen: The spawned backend process instance.

    Raises:
        None

    Examples:
        >>> proc = _start_backend()
    """
    fastapi_cmd = [
        "uvicorn",
        "src.backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    print("[Launcher] Launching FastAPI backend...", flush=True)
    return subprocess.Popen(fastapi_cmd)


def _start_frontend() -> subprocess.Popen:
    """Spawns the Streamlit frontend subprocess.

    High level role: Asynchronously launches the Streamlit app.
    It constructs the streamlit command for port 8501 and executes it.

    Args:
        None

    Returns:
        subprocess.Popen: The spawned frontend process instance.

    Raises:
        None

    Examples:
        >>> proc = _start_frontend()
    """
    streamlit_cmd = [
        "streamlit",
        "run",
        "src/streamlit_app/app.py",
        "--server.port",
        "8501",
        "--server.address",
        "0.0.0.0",
    ]
    print("[Launcher] Launching Streamlit frontend...", flush=True)
    return subprocess.Popen(streamlit_cmd)


def _monitor_processes(
    fastapi_proc: subprocess.Popen, streamlit_proc: subprocess.Popen
) -> None:
    """Monitors both backend and frontend processes in an active watch loop.

    High level role: Acts as a process watchdog and supervisor.
    It polls both subprocesses continuously. If either exits, it exits the launcher
    with that process's return code. It also intercepts KeyboardInterrupt to terminate
    both subprocesses cleanly.

    Args:
        fastapi_proc (subprocess.Popen): Backend process instance.
        streamlit_proc (subprocess.Popen): Frontend process instance.

    Returns:
        None

    Raises:
        SystemExit: If either process exits or on KeyboardInterrupt.

    Examples:
        >>> _monitor_processes(fastapi_proc, streamlit_proc)
    """
    try:
        while True:
            # Check if either process terminated
            if fastapi_proc.poll() is not None:
                print(
                    f"[Launcher] FastAPI backend exited with code {fastapi_proc.returncode}",
                    flush=True,
                )
                sys.exit(fastapi_proc.returncode)
            if streamlit_proc.poll() is not None:
                print(
                    f"[Launcher] Streamlit frontend exited with code {streamlit_proc.returncode}",
                    flush=True,
                )
                sys.exit(streamlit_proc.returncode)
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Launcher] Terminating subprocesses...", flush=True)
        fastapi_proc.terminate()
        streamlit_proc.terminate()
        sys.exit(0)


def main() -> None:
    """Main execution entry point.

    High level role: Configures the OLLAMA_HOST environment variable with the
    detected gateway IP and launches uvicorn and streamlit as subprocesses.
    It delegates environment setup, process startup, and monitoring loop logic to
    specialized helpers to ensure adherence to layout and line length constraints.

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: If either the FastAPI backend or the Streamlit frontend exits,
            repropagating their exit status.

    Examples:
        >>> main()
    """
    gateway_ip = get_gateway_ip()
    _configure_env(gateway_ip)
    fastapi_proc = _start_backend()
    streamlit_proc = _start_frontend()
    _monitor_processes(fastapi_proc, streamlit_proc)


if __name__ == "__main__":
    main()
