#!/usr/bin/env python
"""
Quick test script to verify out lap functionality
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "actimes_project.settings")
django.setup()

from laptimes.models import Session  # noqa: E402


def test_outlap_functionality():
    print("🔍 Testing Out Lap Functionality")
    print("=" * 50)

    # Get a session
    session = Session.objects.first()
    if not session:
        print("❌ No sessions found. Upload a JSON file first.")
        return

    print(f"📊 Testing session: {session}")
    print()

    # Get out laps and racing laps
    out_laps = session.laps.filter(lap_number=0)
    racing_laps = session.laps.filter(lap_number__gt=0)

    print(f"📈 Out laps (lap_number=0): {out_laps.count()}")
    print(f"🏁 Racing laps (lap_number>0): {racing_laps.count()}")
    print()

    if out_laps.exists():
        print("🟠 OUT LAP EXAMPLES:")
        for lap in out_laps[:3]:
            print(
                f"   Driver: {lap.driver_name}, Lap: {lap.lap_number}, Time: {lap.format_time()}"
            )
        print()

    if racing_laps.exists():
        print("🏎️  RACING LAP EXAMPLES:")
        for lap in racing_laps[:3]:
            print(
                f"   Driver: {lap.driver_name}, Lap: {lap.lap_number}, Time: {lap.format_time()}"
            )
        print()

    # Test fastest lap calculation (should exclude out laps)
    fastest_lap = session.get_fastest_lap()
    if fastest_lap:
        print(
            f"⚡ Fastest lap: {fastest_lap.driver_name}, Lap {fastest_lap.lap_number}, {fastest_lap.format_time()}"
        )
        if fastest_lap.lap_number == 0:
            print("❌ ERROR: Fastest lap should not be an out lap!")
        else:
            print("✅ Correct: Fastest lap excludes out laps")

    print("\n🎨 TEMPLATE TEST:")
    print('Out lap badge should show: <span class="badge bg-outlap">Out</span>')
    print(
        'Racing lap badge should show: <span class="badge bg-primary">[lap_number]</span>'
    )
    print('Out lap row should have: class="table-outlap"')

    print("\n🚀 To test visually:")
    print("1. Run: source .venv/bin/activate && python manage.py runserver")
    print("2. Go to: http://127.0.0.1:8000/")
    print("3. Click on a session to view lap details")
    print("4. Look for orange 'Out' badges and orange row highlighting")
    print("5. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R) to clear cache")


if __name__ == "__main__":
    test_outlap_functionality()
