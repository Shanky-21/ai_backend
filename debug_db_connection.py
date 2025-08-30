#!/usr/bin/env python3
"""
Debug database connection issues
"""
import os

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed")

def test_basic_connection():
    """Test basic database connection with detailed error info."""
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    
    print(f"🔧 Database URL: {database_url[:50]}..." if database_url else "❌ No DATABASE_URL found")
    
    if not database_url:
        print("❌ DATABASE_URL or POSTGRES_URL environment variable not set")
        return False
    
    try:
        print("📦 Testing psycopg import...")
        import psycopg
        from psycopg.rows import dict_row
        print("✅ psycopg imported successfully")
        
        print("🔌 Attempting database connection...")
        conn = psycopg.connect(database_url, row_factory=dict_row)
        print("✅ Connection established!")
        
        print("🔍 Testing basic query...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database version: {version['version'][:100]}...")
        
        print("📋 Testing table existence...")
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table['table_name']}")
        
        conn.close()
        print("✅ Connection test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to provide more specific error info
        if "getaddrinfo failed" in str(e):
            print("💡 DNS resolution failed - check hostname in DATABASE_URL")
        elif "authentication failed" in str(e).lower():
            print("💡 Authentication failed - check username/password")
        elif "does not exist" in str(e):
            print("💡 Database does not exist - check database name")
        elif "connection refused" in str(e):
            print("💡 Connection refused - check host/port")
        
        return False

def test_environment_vars():
    """Test environment variable loading."""
    print("🔧 Environment Variables Check:")
    
    vars_to_check = [
        'DATABASE_URL',
        'POSTGRES_URL', 
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT'
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'PASSWORD' in var:
                print(f"  {var}: ***{value[-4:] if len(value) > 4 else '***'}")
            else:
                print(f"  {var}: {value[:50]}{'...' if len(value) > 50 else ''}")
        else:
            print(f"  {var}: ❌ NOT SET")

if __name__ == "__main__":
    print("🐛 Database Connection Debug")
    print("=" * 40)
    
    test_environment_vars()
    print("\n" + "=" * 40)
    test_basic_connection()
