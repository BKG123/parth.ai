#!/usr/bin/env python3
"""Quick status check for Streamlit app setup."""

import sys
import os
from pathlib import Path

def check_status():
    """Check if all components are ready."""
    
    checks = []
    
    # Check files exist
    files_to_check = [
        "app_streamlit.py",
        "run_streamlit.sh",
        "STREAMLIT_README.md",
        "test_prompts.py",
        "check_user.py",
        "IMPLEMENTATION_SUMMARY.md",
    ]
    
    print("=" * 70)
    print("🪶 PARTH AI STREAMLIT - STATUS CHECK")
    print("=" * 70)
    print()
    
    print("📁 FILE CHECKS:")
    print("-" * 70)
    for file in files_to_check:
        exists = Path(file).exists()
        status = "✅" if exists else "❌"
        checks.append(exists)
        print(f"{status} {file}")
    print()
    
    # Check virtual environment
    print("🐍 ENVIRONMENT CHECKS:")
    print("-" * 70)
    venv_exists = Path(".venv").exists()
    print(f"{'✅' if venv_exists else '❌'} Virtual environment (.venv)")
    checks.append(venv_exists)
    
    # Check if streamlit is importable
    try:
        import streamlit
        print(f"✅ Streamlit installed (v{streamlit.__version__})")
        checks.append(True)
    except ImportError:
        print("❌ Streamlit not installed")
        checks.append(False)
    
    # Check if agent_manager is importable
    try:
        from ai.agent_manager import AgentManager
        print("✅ AgentManager importable")
        checks.append(True)
    except ImportError as e:
        print(f"❌ AgentManager import failed: {e}")
        checks.append(False)
    print()
    
    # Check database connection
    print("🗄️  DATABASE CHECKS:")
    print("-" * 70)
    try:
        import asyncio
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        async def check_db():
            try:
                async with AsyncSessionLocal() as db:
                    await db.execute(text("SELECT 1"))
                return True
            except Exception as e:
                print(f"   Error: {e}")
                return False
        
        db_ok = asyncio.run(check_db())
        print(f"{'✅' if db_ok else '❌'} Database connection")
        checks.append(db_ok)
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        checks.append(False)
    
    # Check test user
    try:
        from database import AsyncSessionLocal
        from models.models import User
        from services.services import BaseCRUD
        
        async def check_user():
            user_crud = BaseCRUD(User)
            async with AsyncSessionLocal() as db:
                user = await user_crud.get(db, id=1)
                return user is not None
        
        user_exists = asyncio.run(check_user())
        print(f"{'✅' if user_exists else '❌'} Test user (ID=1) exists")
        checks.append(user_exists)
    except Exception as e:
        print(f"❌ User check failed: {e}")
        checks.append(False)
    print()
    
    # Check if app is running
    print("🚀 APP STATUS:")
    print("-" * 70)
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    app_running = sock.connect_ex(('localhost', 8501)) == 0
    sock.close()
    print(f"{'✅' if app_running else '⚠️ '} Streamlit app {'running' if app_running else 'not running'}")
    
    if app_running:
        print("   → Open: http://localhost:8501")
    else:
        print("   → Start with: ./run_streamlit.sh")
    print()
    
    # Summary
    print("=" * 70)
    total = len(checks)
    passed = sum(checks)
    print(f"📊 SUMMARY: {passed}/{total} checks passed")
    print("=" * 70)
    
    if passed == total:
        print("✅ ALL SYSTEMS GO! Ready to test.")
        if not app_running:
            print("\n💡 Start the app with: ./run_streamlit.sh")
        return 0
    else:
        print("⚠️  Some checks failed. Review above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(check_status())
