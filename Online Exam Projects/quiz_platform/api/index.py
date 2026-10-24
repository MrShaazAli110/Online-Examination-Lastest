import os
import sys

# Add project root directory to sys.path so modules like `app` can be imported
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app

# Serverless handler adapter (Mangum) for AWS Lambda and Netlify Functions
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None
