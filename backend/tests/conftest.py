"""
VIDUR Test Suite - Shared Fixtures
Purpose: Provide the minimum required environment variables so that
`app.config.settings` (imported transitively by almost every module)
can be constructed during test collection, without requiring a real
`.env` file or live MongoDB/ChromaDB servers.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-do-not-use-in-prod")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
