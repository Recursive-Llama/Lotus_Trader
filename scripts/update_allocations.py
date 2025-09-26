#!/usr/bin/env python3
"""
Allocation Update Script

This script provides an easy way to update allocation percentages across the entire system.
All changes are made through the centralized allocation manager.

Usage:
    python scripts/update_allocations.py --help
    python scripts/update_allocations.py --social-excellent 25.0
    python scripts/update_allocations.py --gem-conservative 8.0
    python scripts/update_allocations.py --show-current
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from config.allocation_manager import AllocationManager


def show_current_allocations(manager: AllocationManager):
    """Display current allocation configuration"""
    print("=== Current Allocation Configuration ===")
    print()
    
    print("Social Media Curators:")
    print(f"  Excellent (≥0.8): {manager.get_social_curator_allocation(0.9):.1f}%")
    print(f"  Good (≥0.6): {manager.get_social_curator_allocation(0.7):.1f}%")
    print(f"  Acceptable (<0.6): {manager.get_social_curator_allocation(0.5):.1f}%")
    print()
    
    print("Gem Bot Signals:")
    print(f"  Conservative: {manager.get_gem_bot_allocation('conservative'):.1f}%")
    print(f"  Balanced: {manager.get_gem_bot_allocation('balanced'):.1f}%")
    print(f"  Risky: {manager.get_gem_bot_allocation('risky'):.1f}%")
    print()
    
    print("Test Mode (reduced for safety):")
    print(f"  Social Curators: {manager.get_social_curator_allocation(0.9, test_mode=True):.1f}%")
    print(f"  Gem Bot: {manager.get_gem_bot_allocation('conservative', test_mode=True):.1f}%")


def update_allocation(manager: AllocationManager, category: str, key: str, value: float):
    """Update a specific allocation value"""
    try:
        manager.update_allocation(category, key, value)
        print(f"✅ Updated {category}.{key} to {value}%")
    except ValueError as e:
        print(f"❌ Error updating allocation: {e}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Update allocation percentages across the trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current allocations
  python scripts/update_allocations.py --show-current
  
  # Update social curator allocations
  python scripts/update_allocations.py --social-excellent 25.0
  python scripts/update_allocations.py --social-good 10.0
  python scripts/update_allocations.py --social-acceptable 8.0
  
  # Update gem bot allocations
  python scripts/update_allocations.py --gem-conservative 8.0
  python scripts/update_allocations.py --gem-balanced 6.0
  python scripts/update_allocations.py --gem-risky 3.0
  
  # Update test mode multipliers
  python scripts/update_allocations.py --test-social-multiplier 0.15
  python scripts/update_allocations.py --test-gem-multiplier 0.25
        """
    )
    
    # Social curator allocations
    parser.add_argument('--social-excellent', type=float, help='Excellent curator allocation percentage')
    parser.add_argument('--social-good', type=float, help='Good curator allocation percentage')
    parser.add_argument('--social-acceptable', type=float, help='Acceptable curator allocation percentage')
    
    # Gem bot allocations
    parser.add_argument('--gem-conservative', type=float, help='Conservative gem bot allocation percentage')
    parser.add_argument('--gem-balanced', type=float, help='Balanced gem bot allocation percentage')
    parser.add_argument('--gem-risky', type=float, help='Risky gem bot allocation percentage')
    
    # Test mode multipliers
    parser.add_argument('--test-social-multiplier', type=float, help='Test mode social curator multiplier (0.0-1.0)')
    parser.add_argument('--test-gem-multiplier', type=float, help='Test mode gem bot multiplier (0.0-1.0)')
    
    # Display options
    parser.add_argument('--show-current', action='store_true', help='Show current allocation configuration')
    parser.add_argument('--save', action='store_true', help='Save changes to configuration file')
    
    args = parser.parse_args()
    
    # Initialize allocation manager
    try:
        manager = AllocationManager()
    except Exception as e:
        print(f"❌ Failed to initialize allocation manager: {e}")
        return 1
    
    # Show current allocations if requested
    if args.show_current:
        show_current_allocations(manager)
        return 0
    
    # Check if any updates were requested
    updates_made = False
    
    # Social curator updates
    if args.social_excellent is not None:
        if update_allocation(manager, 'social_curators', 'excellent_allocation', args.social_excellent):
            updates_made = True
    
    if args.social_good is not None:
        if update_allocation(manager, 'social_curators', 'good_allocation', args.social_good):
            updates_made = True
    
    if args.social_acceptable is not None:
        if update_allocation(manager, 'social_curators', 'acceptable_allocation', args.social_acceptable):
            updates_made = True
    
    # Gem bot updates
    if args.gem_conservative is not None:
        if update_allocation(manager, 'gem_bot', 'conservative_allocation', args.gem_conservative):
            updates_made = True
    
    if args.gem_balanced is not None:
        if update_allocation(manager, 'gem_bot', 'balanced_allocation', args.gem_balanced):
            updates_made = True
    
    if args.gem_risky is not None:
        if update_allocation(manager, 'gem_bot', 'risky_allocation', args.gem_risky):
            updates_made = True
    
    # Test mode updates
    if args.test_social_multiplier is not None:
        if 0.0 <= args.test_social_multiplier <= 1.0:
            if update_allocation(manager, 'test_mode', 'social_curators_multiplier', args.test_social_multiplier):
                updates_made = True
        else:
            print("❌ Test social multiplier must be between 0.0 and 1.0")
    
    if args.test_gem_multiplier is not None:
        if 0.0 <= args.test_gem_multiplier <= 1.0:
            if update_allocation(manager, 'test_mode', 'gem_bot_multiplier', args.test_gem_multiplier):
                updates_made = True
        else:
            print("❌ Test gem multiplier must be between 0.0 and 1.0")
    
    # Show updated allocations
    if updates_made:
        print()
        show_current_allocations(manager)
        
        # Save if requested
        if args.save:
            try:
                manager.save_config()
                print("\n✅ Changes saved to configuration file")
            except Exception as e:
                print(f"\n❌ Failed to save configuration: {e}")
                return 1
        else:
            print("\n💡 Use --save to persist changes to the configuration file")
    else:
        print("No updates specified. Use --help for usage information.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
