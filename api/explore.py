"""
Vercel serverless function for /api/explore.

Vercel maps api/explore.py to the URL /api/explore and looks for a top-level
class named `handler` that subclasses BaseHTTPRequestHandler. The real
implementation lives in dispatch/web.py so the local dev server and every
Vercel function share one code path.
"""

import os
import sys

# Make the repo root importable so `dispatch` resolves inside the function.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dispatch.web import DispatchHandler  # noqa: E402


class handler(DispatchHandler):  # noqa: N801 (name required by Vercel)
    pass
