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
            user_prefix="Demo-With-Exclusion", 
            enable_firm_exclusion=True,
            enable_contact_inclusion=False
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_with_inclusion():
    """Demo filter with contact inclusion enabled"""
    print("\n🚀 DEMO: Tiered Filter WITH Contact Inclusion")
    print("=" * 60)
    
    filter_tool = TieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Demo-With-Inclusion", 
            enable_firm_exclusion=False,
            enable_contact_inclusion=True
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_with_both():
    """Demo filter with both firm exclusion and contact inclusion enabled"""
    print("\n🚀 DEMO: Tiered Filter WITH Both Exclusion AND Inclusion")
    print("=" * 60)
    
    filter_tool = TieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Demo-With-Both", 
            enable_firm_exclusion=True,
            enable_contact_inclusion=True
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_without_exclusion():
    """Demo filter without firm exclusion"""
    print("\n🚀 DEMO: Tiered Filter WITHOUT Any Special Processing")
    print("=" * 60)
    
    filter_tool = TieredFilter()
    try:
        output_file = filter_tool.process_contacts(
            user_prefix="Demo-Standard", 
            enable_firm_exclusion=False,
            enable_contact_inclusion=False
        )
        print(f"✅ Success! Output: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 ADVANCED FILTERING DEMO")
    print("This demo shows different filtering configurations:")
    print("- Firm exclusion: Remove entire firms")
    print("- Contact inclusion: Force specific individuals through filters")
    print("- Combined: Both exclusion and inclusion together")
    print("Check the output files to see the difference in contact counts\n")
    
    # Run all demos
    demo_with_exclusion()
    demo_with_inclusion()
    demo_with_both()
    demo_without_exclusion()
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed! Check the output folder for results.")
    print("Compare the different output files to see the impact of each feature:")
    print("- 'With-Exclusion': Firms removed, standard filtering")
    print("- 'With-Inclusion': Standard filtering + forced contacts")
    print("- 'With-Both': Firms removed + forced contacts")
    print("- 'Standard': Baseline with no special processing")
