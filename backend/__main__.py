"""Run the ForgeRunner backend: `python -m backend`.

It listens on 127.0.0.1 (this PC only) unless --host says otherwise. Use --host 0.0.0.0 only if you mean to serve the
dashboard to other machines on your network: the API has no login.
"""
import argparse

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m backend", description="Run the ForgeRunner backend.")
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help=f"address to listen on (default {DEFAULT_HOST}: this PC only)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default {DEFAULT_PORT})")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    uvicorn.run("backend.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
