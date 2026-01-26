
import asyncio
import sys
sys.path.insert(0, '/app/services')

from common.db import init_db
# Import models to register them with Base.metadata
from common import models 

async def main():
    print("--- Database Initialization ---")
    print("Registering models...")
    # Just accessing models module ensures they are imported
    print(f"Models found: {dir(models)}")
    
    print("Creating tables...")
    try:
        await init_db()
        print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
