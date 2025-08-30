import os
import glob
from pathlib import Path

def get_test_files() -> list:
    """Get test files from resources/data directory."""
    print("📁 Looking for test files in resources/data...")
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "resources" / "data"
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return []
    
    # Find CSV and Excel files
    csv_files = list(data_dir.glob("*.csv"))
    excel_files = list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.xls"))
    
    all_files = csv_files + excel_files
    
    print(f"📊 Found {len(all_files)} data files:")
    for file in all_files:
        print(f"  - {file.name}")
    
    return [str(file) for file in all_files]

def test_workflow_with_real_data():
    """Test the AI workflow with real data files."""
    print("🧪 Testing workflow with real data...")
    
    # Import here to avoid startup issues
    from app.ai_workflow import run_complete_workflow
    
    # Get test files
    test_files = get_test_files()
    
    if not test_files:
        print("❌ No test files found. Please add CSV/Excel files to resources/data/")
        return
    
    try:
        result = run_complete_workflow(
            files=test_files,
            business_description="We are a business looking to gain insights from our data to improve operations and revenue"
        )
        
        print(f"📋 Workflow Status: {result['status']}")
        
        if result['status'] == 'success':
            data = result['data']
            print(f"🎯 Business Understanding: {data.get('business_understanding', 'N/A')}")
            print(f"📊 Generated Insights: {len(data.get('final_insights', []))}")
            
            for insight in data.get('final_insights', []):
                print(f"  - {insight['title']} ({insight['status']})")
                if 'insights' in insight:
                    summary = insight['insights'].get('executive_summary', 'No summary')
                    print(f"    Summary: {summary[:100]}...")
        else:
            print(f"❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def list_available_files():
    """List what files are available for testing."""
    print("📋 Available test files:")
    test_files = get_test_files()
    
    if not test_files:
        print("❌ No files found in resources/data/")
        print("💡 Add your CSV or Excel files to resources/data/ directory")
        return
        
    for file_path in test_files:
        try:
            import pandas as pd
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            filename = os.path.basename(file_path)
            print(f"  📄 {filename}: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"    Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
        except Exception as e:
            print(f"  ❌ {os.path.basename(file_path)}: Error reading file - {e}")

if __name__ == "__main__":
    print("🚀 Business Insights AI - Test Runner")
    print("=" * 50)
    
    list_available_files()
    print()
    test_workflow_with_real_data()
