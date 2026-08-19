import sys
import os

# Add root directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import serverless_wsgi
    from app import app, init_db

    # Ensure DB tables exist on cold start
    init_db()

    def handler(event, context):
        return serverless_wsgi.handle_request(app, event, context)

except ImportError:
    from app import app, init_db
    init_db()

    def handler(event, context):
        # Fallback direct response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": "<h1>Application Initialized</h1>"
        }
