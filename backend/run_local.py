#!/usr/bin/env python3
"""
Local development server for Wink Analytics Platform.
Uses SQLite database and simplified setup for testing.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set environment variables for local development
os.environ['DATABASE_URL'] = 'sqlite:///./wink_store_local.db'
os.environ['STORE_ID'] = 'local_store_001'
os.environ['STORE_NAME'] = 'Local Test Store'
os.environ['ALLOW_STORE_CREATION'] = 'true'
os.environ['JWT_SECRET_KEY'] = 'local-dev-secret-key-change-in-production'

# Import after setting environment
from dotenv import load_dotenv
load_dotenv('.env.local', override=True)

def create_test_user():
    """Create a test user for local development."""
    try:
        from src.auth.auth_manager import get_auth_manager
        from src.database.database import get_database

        # Initialize database
        db = get_database()
        db.create_tables()

        # Create auth manager
        auth = get_auth_manager()

        # Create test store and user
        with db.get_session() as session:
            try:
                store, user = auth.create_store_and_owner(
                    db=session,
                    store_name="Local Test Store",
                    owner_email="admin@localhost",
                    owner_password="admin123"
                )
                print(f"✅ Created test store: {store.name}")
                print(f"✅ Created test user: {user.email}")
                print(f"📧 Login with: admin@localhost / admin123")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("✅ Test user already exists: admin@localhost / admin123")
                else:
                    raise e

    except Exception as e:
        print(f"❌ Error creating test user: {e}")

def main():
    print("🚀 Starting Wink Analytics Platform (Local Development)")
    print("=" * 60)

    # Create test user
    create_test_user()

    print("\n🌐 Starting local server...")
    print("📱 Frontend: http://localhost:3000")
    print("🔗 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔐 Login: admin@localhost / admin123")
    print("=" * 60)

    # Start the server
    import uvicorn
    from src.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()