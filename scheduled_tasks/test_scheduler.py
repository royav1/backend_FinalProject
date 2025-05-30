import os
import sys
import django
import asyncio

# Manual trigger used to test the scheduled scraping functionality directly

# ✅ Force Python to treat "backend/" as the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproj.settings")
django.setup()

# ✅ Import AFTER Django setup
from scheduled_tasks.scheduler import async_scraping_wrapper

if __name__ == "__main__":
    asyncio.run(async_scraping_wrapper())
