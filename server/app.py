"""
server/app.py — OpenEnv multi-mode server entry point.
The 'server' script calls main() which starts the uvicorn server.
"""
import uvicorn
import os
import sys

# Ensure the root directory is in the path so we can import 'app'
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app import app


def main():
    """Entry point for the OpenEnv server script."""
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)


if __name__ == "__main__":
    main()
