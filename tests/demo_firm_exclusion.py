#!/usr/bin/env python3
"""
Demo script showing firm exclusion functionality
Run this to test firm exclusion without interactive prompts
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from tiered_filter import TieredFilter

def demo_with_exclusion():
    """Demo filter with firm exclusion enabled"""
    print("🚀 DEMO: Tiered Filter WITH Firm Exclusion")
    print("=" * 60)
    
    filter_tool = TieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Unified-With-Exclusion", 
            enable_firm_exclusion=True
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_without_exclusion():
    """Demo filter without firm exclusion"""
    print("\n🚀 DEMO: Tiered Filter WITHOUT Firm Exclusion")
    print("=" * 60)
    
    filter_tool = TieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Unified-No-Exclusion", 
            enable_firm_exclusion=False
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 FIRM EXCLUSION DEMO")
    print("This demo shows the difference between running with and without firm exclusion")
    print("Check the output files to see the difference in contact counts\n")
    
    # Run both demos
    demo_with_exclusion()
    demo_without_exclusion()
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed! Check the output folder for results.")
    print("Files ending with 'With-Exclusion' will have fewer contacts from excluded firms.")
    print("Files ending with 'No-Exclusion' will have all contacts.")
