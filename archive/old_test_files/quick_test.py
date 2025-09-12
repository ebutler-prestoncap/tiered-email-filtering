#!/usr/bin/env python3
"""
Quick test of the main script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consolidated_tiered_filter import ConsolidatedTieredFilter

def main():
    print("Testing consolidated tiered filter...")
    
    # Create filter instance
    filter_tool = ConsolidatedTieredFilter()
    
    # Test the process
    try:
        output_file = filter_tool.process_contacts("Test-Contacts")
        print(f"Success! Output saved to: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
