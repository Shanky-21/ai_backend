#!/usr/bin/env python3
"""
Inspect the existing database schema
"""
import os

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def inspect_database_schema():
    """Inspect the existing database schema."""
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        database_url = os.getenv('DATABASE_URL')
        conn = psycopg.connect(database_url, row_factory=dict_row)
        
        print("🔍 Inspecting Database Schema")
        print("=" * 50)
        
        with conn.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table['table_name']
                print(f"\n📊 Table: {table_name}")
                print("-" * 30)
                
                # Get column information
                cursor.execute("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position;
                """, (table_name,))
                
                columns = cursor.fetchall()
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                    print(f"  {col['column_name']:<20} {col['data_type']:<15} {nullable}{default}")
                
                # Get sample data (first 3 rows)
                try:
                    cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3;')
                    sample_data = cursor.fetchall()
                    
                    if sample_data:
                        print(f"\n📋 Sample Data ({len(sample_data)} rows):")
                        for i, row in enumerate(sample_data, 1):
                            print(f"  Row {i}: {dict(row)}")
                    else:
                        print(f"\n📋 Table is empty")
                        
                except Exception as e:
                    print(f"\n⚠️  Could not fetch sample data: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error inspecting schema: {e}")

if __name__ == "__main__":
    inspect_database_schema()
