#!/usr/bin/env python3
"""
Analyze learning_lessons table to understand what's stored.

Usage:
    PYTHONPATH=src python tools/analyze_learning_lessons.py
"""

import os
import sys
from pathlib import Path
from collections import Counter, defaultdict
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("LEARNING LESSONS TABLE ANALYSIS")
    print("=" * 80)
    
    # Get total count
    count_result = sb.table("learning_lessons").select("id", count="exact").limit(1).execute()
    total_count = count_result.count if hasattr(count_result, 'count') else 0
    
    if total_count == 0:
        print("❌ No lessons found in table")
        return
    
    print(f"\n📊 Total Lessons: {total_count:,}")
    
    # Fetch all lessons (with pagination if needed)
    all_lessons = []
    page_size = 1000
    offset = 0
    
    while True:
        result = sb.table("learning_lessons").select("*").range(offset, offset + page_size - 1).execute()
        if not result.data:
            break
        all_lessons.extend(result.data)
        offset += page_size
        if len(result.data) < page_size:
            break
    
    print(f"📥 Fetched {len(all_lessons):,} lessons\n")
    
    # Analysis 1: By module
    print("=" * 80)
    print("1. BY MODULE")
    print("=" * 80)
    module_counts = Counter(l.get("module") for l in all_lessons)
    for module, count in module_counts.most_common():
        print(f"  {module or '(null)':<10} {count:>6,} ({count/len(all_lessons)*100:.1f}%)")
    
    # Analysis 2: By lesson_type
    print("\n" + "=" * 80)
    print("2. BY LESSON TYPE")
    print("=" * 80)
    lesson_type_counts = Counter(l.get("lesson_type") for l in all_lessons)
    for lesson_type, count in lesson_type_counts.most_common():
        print(f"  {lesson_type or '(null)':<30} {count:>6,} ({count/len(all_lessons)*100:.1f}%)")
    
    # Analysis 3: By pattern_key
    print("\n" + "=" * 80)
    print("3. BY PATTERN KEY (Top 20)")
    print("=" * 80)
    pattern_counts = Counter(l.get("pattern_key") for l in all_lessons)
    for pattern, count in pattern_counts.most_common(20):
        print(f"  {pattern or '(null)':<40} {count:>6,}")
    
    # Analysis 4: By action_category
    print("\n" + "=" * 80)
    print("4. BY ACTION CATEGORY")
    print("=" * 80)
    action_counts = Counter(l.get("action_category") for l in all_lessons)
    for action, count in action_counts.most_common():
        print(f"  {action or '(null)':<30} {count:>6,} ({count/len(all_lessons)*100:.1f}%)")
    
    # Analysis 5: N value distribution
    print("\n" + "=" * 80)
    print("5. N VALUE DISTRIBUTION")
    print("=" * 80)
    n_values = [l.get("n", 0) for l in all_lessons]
    if n_values:
        print(f"  Min:     {min(n_values):>6,}")
        print(f"  Max:     {max(n_values):>6,}")
        print(f"  Mean:    {sum(n_values)/len(n_values):>6,.1f}")
        print(f"  Median:  {sorted(n_values)[len(n_values)//2]:>6,}")
        
        # Distribution buckets
        buckets = {
            "1-10": 0,
            "11-33": 0,
            "34-50": 0,
            "51-100": 0,
            "101-200": 0,
            "201+": 0,
        }
        for n in n_values:
            if n <= 10:
                buckets["1-10"] += 1
            elif n <= 33:
                buckets["11-33"] += 1
            elif n <= 50:
                buckets["34-50"] += 1
            elif n <= 100:
                buckets["51-100"] += 1
            elif n <= 200:
                buckets["101-200"] += 1
            else:
                buckets["201+"] += 1
        
        print("\n  Distribution:")
        for bucket, count in buckets.items():
            print(f"    {bucket:>8} {count:>6,} ({count/len(n_values)*100:.1f}%)")
    
    # Analysis 6: Scope subset dimensions
    print("\n" + "=" * 80)
    print("6. SCOPE SUBSET DIMENSIONS (Top 10 most common)")
    print("=" * 80)
    scope_keys = Counter()
    scope_examples = defaultdict(list)
    
    for lesson in all_lessons:
        scope = lesson.get("scope_subset", {})
        if isinstance(scope, dict):
            for key in scope.keys():
                scope_keys[key] += 1
                if len(scope_examples[key]) < 3:
                    scope_examples[key].append(scope.get(key))
    
    for key, count in scope_keys.most_common(10):
        examples = scope_examples[key][:3]
        examples_str = ", ".join(str(e) for e in examples if e is not None)
        print(f"  {key:<30} {count:>6,}  (examples: {examples_str})")
    
    # Analysis 7: Status distribution
    print("\n" + "=" * 80)
    print("7. BY STATUS")
    print("=" * 80)
    status_counts = Counter(l.get("status") for l in all_lessons)
    for status, count in status_counts.most_common():
        print(f"  {status or '(null)':<20} {count:>6,} ({count/len(all_lessons)*100:.1f}%)")
    
    # Analysis 8: Sample lessons (show structure)
    print("\n" + "=" * 80)
    print("8. SAMPLE LESSONS (showing structure)")
    print("=" * 80)
    
    # Show examples of different lesson types
    seen_types = set()
    for lesson in all_lessons:
        lesson_type = lesson.get("lesson_type")
        if lesson_type and lesson_type not in seen_types:
            seen_types.add(lesson_type)
            print(f"\n  Example: {lesson_type}")
            print(f"    ID: {lesson.get('id')}")
            print(f"    Module: {lesson.get('module')}")
            print(f"    Pattern Key: {lesson.get('pattern_key')}")
            print(f"    Action Category: {lesson.get('action_category')}")
            print(f"    N: {lesson.get('n')}")
            print(f"    Scope Subset: {lesson.get('scope_subset')}")
            print(f"    Stats Keys: {list(lesson.get('stats', {}).keys())}")
            if len(seen_types) >= 5:
                break
    
    # Analysis 9: Tuning rates lessons specifically
    print("\n" + "=" * 80)
    print("9. TUNING RATES LESSONS (if any)")
    print("=" * 80)
    tuning_lessons = [l for l in all_lessons if l.get("lesson_type") == "tuning_rates"]
    if tuning_lessons:
        print(f"  Found {len(tuning_lessons):,} tuning_rates lessons")
        
        # Show stats structure
        if tuning_lessons:
            sample = tuning_lessons[0]
            stats = sample.get("stats", {})
            print(f"\n  Sample stats structure:")
            for key, value in stats.items():
                print(f"    {key}: {value}")
        
        # Pattern key breakdown for tuning rates
        tuning_patterns = Counter(l.get("pattern_key") for l in tuning_lessons)
        print(f"\n  By pattern_key:")
        for pattern, count in tuning_patterns.most_common(10):
            print(f"    {pattern:<40} {count:>6,}")
    else:
        print("  No tuning_rates lessons found")
    
    # Analysis 10: Check for potential issues
    print("\n" + "=" * 80)
    print("10. POTENTIAL ISSUES")
    print("=" * 80)
    
    issues = []
    
    # Check for null n values
    null_n = [l for l in all_lessons if l.get("n") is None or l.get("n") == 0]
    if null_n:
        issues.append(f"  ⚠️  {len(null_n):,} lessons with n=0 or null")
    
    # Check for empty scope_subset
    empty_scope = [l for l in all_lessons if not l.get("scope_subset") or l.get("scope_subset") == {}]
    if empty_scope:
        issues.append(f"  ℹ️  {len(empty_scope):,} lessons with empty scope_subset (global lessons)")
    
    # Check for very high n values (might indicate aggregation issues)
    high_n = [l for l in all_lessons if l.get("n", 0) > 1000]
    if high_n:
        issues.append(f"  ⚠️  {len(high_n):,} lessons with n > 1000 (check for aggregation issues)")
    
    # Check for duplicate pattern_key + scope combinations
    unique_keys = set()
    duplicates = 0
    for lesson in all_lessons:
        key = (lesson.get("pattern_key"), str(lesson.get("scope_subset")), lesson.get("action_category"))
        if key in unique_keys:
            duplicates += 1
        else:
            unique_keys.add(key)
    
    if duplicates > 0:
        issues.append(f"  ⚠️  {duplicates:,} potential duplicate lessons (same pattern_key + scope + action_category)")
    else:
        issues.append(f"  ✅ No duplicate lessons detected")
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("  ✅ No obvious issues detected")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

