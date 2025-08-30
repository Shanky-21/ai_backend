#!/usr/bin/env python3
"""
View detailed insights from the Business Insights AI test
"""
import os
import sys
import json
from datetime import datetime

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

def run_and_show_insights():
    """Run workflow and display detailed insights."""
    print("🔍 Running Business Insights AI Analysis...")
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
            business_description="We are a retail business looking to optimize our sales performance and understand customer patterns from our transaction data"
        )
        
        print(f"\n📋 Workflow Status: {result['status']}")
        
        if result['status'] == 'success':
            data = result['data']
            
            print(f"\n🎯 Business Understanding:")
            print(f"   {data.get('business_understanding', 'N/A')}")
            
            print(f"\n💡 Help Suggestions Generated: {len(data.get('help_suggestions', []))}")
            for i, suggestion in enumerate(data.get('help_suggestions', []), 1):
                print(f"   {i}. {suggestion.get('title', 'N/A')} (Priority: {suggestion.get('priority', 'N/A')})")
                print(f"      Description: {suggestion.get('description', 'N/A')}")
            
            print(f"\n🗂️  File Mappings:")
            for title, mapping in data.get('file_mappings', {}).items():
                files_used = [os.path.basename(f) for f in mapping.get('relevant_files', [])]
                print(f"   {title}: {', '.join(files_used)} (Confidence: {mapping.get('confidence', 'N/A')})")
            
            print(f"\n📊 Generated Insights: {len(data.get('final_insights', []))}")
            print("=" * 60)
            
            for i, insight in enumerate(data.get('final_insights', []), 1):
                print(f"\n🔍 INSIGHT #{i}: {insight.get('title', 'N/A')}")
                print(f"Status: {insight.get('status', 'N/A')} | Priority: {insight.get('priority', 'N/A')}")
                print(f"Files Used: {', '.join(insight.get('files_used', []))}")
                print(f"Generated: {insight.get('generated_at', 'N/A')}")
                
                # Show analysis results
                analysis = insight.get('analysis_results', {})
                print(f"\n📈 Analysis Results:")
                
                # Handle metrics with numpy types
                metrics = analysis.get('metrics', {})
                print(f"  Metrics:")
                for key, value in metrics.items():
                    # Convert numpy types to Python types for display
                    if hasattr(value, 'item'):  # numpy scalar
                        value = value.item()
                    print(f"    {key}: {value}")
                
                print(f"  Key Findings: {analysis.get('key_findings', [])}")
                print(f"  Recommendations: {analysis.get('recommendations', [])}")
                
                # Show visualization details
                visualizations = analysis.get('visualizations', [])
                print(f"  Visualizations: {len(visualizations)} charts generated")
                for j, viz in enumerate(visualizations, 1):
                    viz_title = viz.get('title', f'Chart {j}')
                    viz_type = viz.get('type', 'unknown')
                    viz_data_size = len(viz.get('data', ''))
                    print(f"    Chart {j}: {viz_title} ({viz_type}) - {viz_data_size} bytes")
                
                # Show business insights
                business = insight.get('insights', {})
                print(f"\n💼 Business Insights:")
                print(f"  Executive Summary: {business.get('executive_summary', 'N/A')}")
                print(f"  Key Findings: {business.get('key_findings', [])}")
                print(f"  Recommendations: {business.get('recommendations', [])}")
                print(f"  Next Steps: {business.get('next_steps', [])}")
                
                if analysis.get('error'):
                    print(f"  ⚠️  Error: {analysis.get('error')}")
                
                print("-" * 60)
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Failed to run analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_and_show_insights()
