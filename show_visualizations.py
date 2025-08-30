#!/usr/bin/env python3
"""
Extract and save visualizations from Business Insights AI
"""
import os
import base64
from datetime import datetime

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

def extract_and_save_visualizations():
    """Run workflow and extract visualizations."""
    print("🎨 Extracting Visualizations from Business Insights AI...")
    print("=" * 60)
    
    try:
        from tests.test_basic_workflow import get_test_files
        from app.ai_workflow import run_complete_workflow
        
        # Get test files
        test_files = get_test_files()
        if not test_files:
            print("❌ No test files found in resources/data/")
            return
        
        print(f"📊 Processing {len(test_files)} files:")
        for file in test_files:
            print(f"  - {os.path.basename(file)}")
        
        # Run workflow
        result = run_complete_workflow(
            files=test_files,
            business_description="We are a retail business looking to optimize our sales performance, customer satisfaction, and inventory management"
        )
        
        if result['status'] == 'success':
            data = result['data']
            
            # Create visualizations directory
            viz_dir = "visualizations"
            os.makedirs(viz_dir, exist_ok=True)
            
            print(f"\n📊 Extracting visualizations...")
            
            total_charts = 0
            for i, insight in enumerate(data.get('final_insights', []), 1):
                print(f"\n🔍 INSIGHT #{i}: {insight.get('title', 'N/A')}")
                
                analysis = insight.get('analysis_results', {})
                visualizations = analysis.get('visualizations', [])
                
                print(f"  📈 Found {len(visualizations)} visualizations")
                
                for j, viz in enumerate(visualizations, 1):
                    try:
                        viz_title = viz.get('title', f'Chart_{i}_{j}')
                        viz_data = viz.get('data', '')
                        
                        if viz_data:
                            # Decode base64 image data
                            image_data = base64.b64decode(viz_data)
                            
                            # Create filename
                            safe_title = "".join(c for c in viz_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            filename = f"{viz_dir}/insight_{i}_{safe_title.replace(' ', '_')}.png"
                            
                            # Save image
                            with open(filename, 'wb') as f:
                                f.write(image_data)
                            
                            print(f"    ✅ Saved: {filename}")
                            total_charts += 1
                        else:
                            print(f"    ⚠️  No data for visualization: {viz_title}")
                            
                    except Exception as e:
                        print(f"    ❌ Error saving visualization {j}: {e}")
            
            if total_charts > 0:
                print(f"\n🎉 Successfully saved {total_charts} visualizations to '{viz_dir}/' folder!")
                print(f"📁 You can open the PNG files to view the charts.")
                
                # List saved files
                print(f"\n📋 Saved files:")
                for file in os.listdir(viz_dir):
                    if file.endswith('.png'):
                        file_path = os.path.join(viz_dir, file)
                        file_size = os.path.getsize(file_path)
                        print(f"  - {file} ({file_size} bytes)")
                
                print(f"\n💡 To view visualizations:")
                print(f"  - Open the files in '{viz_dir}/' folder")
                print(f"  - Or run: xdg-open {viz_dir}/")
                
            else:
                print(f"\n⚠️  No visualizations found to extract.")
                
        else:
            print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Failed to extract visualizations: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_and_save_visualizations()
