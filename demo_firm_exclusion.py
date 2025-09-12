#!/usr/bin/env python3
"""
Demo script showing firm exclusion functionality
Run this to test firm exclusion without interactive prompts
"""

from unified_tiered_filter import UnifiedTieredFilter

def demo_unified_with_exclusion():
    """Demo unified filter with firm exclusion enabled"""
    print("🚀 DEMO: Unified Filter WITH Firm Exclusion")
    print("=" * 60)
    
    filter_tool = UnifiedTieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Unified-With-Exclusion", 
            enable_firm_exclusion=True
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_unified_without_exclusion():
    """Demo unified filter without firm exclusion"""
    print("\n🚀 DEMO: Unified Filter WITHOUT Firm Exclusion")
    print("=" * 60)
    
    filter_tool = UnifiedTieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Unified-No-Exclusion", 
            enable_firm_exclusion=False
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 FIRM EXCLUSION DEMO - Using Unified Filter (Recommended)")
    print("This demo shows the difference between running with and without firm exclusion")
    print("Check the output files to see the difference in contact counts\n")
    
    # Run both demos
    demo_unified_with_exclusion()
    demo_unified_without_exclusion()
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed! Check the output folder for results.")
    print("Files ending with 'With-Exclusion' will have fewer contacts from excluded firms.")
    print("Files ending with 'No-Exclusion' will have all contacts.")
    print("\n📝 Note: This demo uses the UNIFIED filter (recommended stable version)")
