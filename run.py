import os
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).resolve().parent
sys.path.append(str(root_dir))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

# Import Django and set up the application
import django
django.setup()

# Import the ASGI application after Django is set up
from web.asgi import application

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'run:application',
        host='127.0.0.1',
        port=8001,
        reload=True,
        reload_dirs=[str(root_dir)],
        ws_ping_interval=20,
        ws_ping_timeout=20,
    ) 