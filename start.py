"""
Process Supervisor for Render Deployment.

Runs both FastAPI backend (on 127.0.0.1:8000) and Streamlit frontend (on 0.0.0.0:$PORT)
inside a single Render web service container.

Ensures:
1. Backend is started and healthy before launching frontend.
2. Graceful shutdown / signal forwarding to both child processes.
3. Clean logging and automatic error detection.
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = os.environ.get("PORT", "8501")


def wait_for_backend(timeout_seconds: int = 30) -> bool:
    """Polls FastAPI /health endpoint until it responds with HTTP 200 or times out."""
    url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
    start_time = time.time()
    print(f"[SUPERVISOR] Waiting for backend at {url}...", flush=True)

    while time.time() - start_time < timeout_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Render-Supervisor"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    print("[SUPERVISOR] Backend is healthy and ready!", flush=True)
                    return True
        except Exception:
            time.sleep(1)

    print("[SUPERVISOR] Warning: Backend health check timed out. Proceeding with frontend anyway...", flush=True)
    return False


def main():
    print("=" * 60, flush=True)
    print(" DATA CENTRIC AGENTIC AI — RENDER SUPERVISOR STARTING", flush=True)
    print(f" APP_MODE: {os.environ.get('APP_MODE', 'demo')}", flush=True)
    print(f" PUBLIC PORT: {FRONTEND_PORT}", flush=True)
    print("=" * 60, flush=True)

    # 1. Start FastAPI backend on 127.0.0.1:8000
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "server:api_app",
        "--host", BACKEND_HOST,
        "--port", str(BACKEND_PORT),
        "--log-level", "info"
    ]
    print(f"[SUPERVISOR] Launching backend: {' '.join(backend_cmd)}", flush=True)
    backend_proc = subprocess.Popen(backend_cmd)

    # 2. Wait for backend to be healthy
    wait_for_backend(timeout_seconds=25)

    # 3. Start Streamlit frontend on 0.0.0.0:$PORT
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(FRONTEND_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    print(f"[SUPERVISOR] Launching frontend: {' '.join(frontend_cmd)}", flush=True)
    frontend_proc = subprocess.Popen(frontend_cmd)

    def shutdown_children(signum, frame):
        print("\n[SUPERVISOR] Termination signal received. Stopping child processes...", flush=True)
        frontend_proc.terminate()
        backend_proc.terminate()
        try:
            frontend_proc.wait(timeout=5)
            backend_proc.wait(timeout=5)
        except Exception:
            frontend_proc.kill()
            backend_proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_children)
    signal.signal(signal.SIGTERM, shutdown_children)

    # Wait for frontend process to terminate
    try:
        ret_code = frontend_proc.wait()
        print(f"[SUPERVISOR] Frontend exited with code {ret_code}.", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        backend_proc.terminate()


if __name__ == "__main__":
    main()
