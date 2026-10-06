"""
Local development API server. Standard library only.

    python3 dev_server.py            # http://localhost:8000
    python3 dev_server.py 9000       # another port

It serves only the /api routes (see dispatch/web.py). During development
the Vite dev server serves the React frontend and proxies /api/* here,
which mirrors how Vercel serves dist/ and api/ in production.

The file is deliberately NOT called server.py, app.py, main.py or index.py:
Vercel treats a root file with one of those names as a Python application
entrypoint, which would hijack the /api routes.
"""

import sys
from http.server import ThreadingHTTPServer

from dispatch.web import DispatchHandler


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), DispatchHandler)
    print(f"Dispatch API at http://localhost:{port}/api/config  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
