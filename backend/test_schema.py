from datetime import date
from pydantic import ValidationError
import sys
import os

sys.path.append(os.getcwd())
from app.schemas.attendance import AttendanceUpdate

try:
    # Test with valid date string
    data = {"status": "present", "date": "2026-04-25"}
    update = AttendanceUpdate(**data)
    print("Valid date string success")
    
    # Test with null date
    data = {"status": "present", "date": None}
    update = AttendanceUpdate(**data)
    print("Null date success")

    # Test with empty string (should fail as it's not a date)
    try:
        data = {"status": "present", "date": ""}
        update = AttendanceUpdate(**data)
        print("Empty string success (unexpected)")
    except ValidationError as e:
        print(f"Empty string failed as expected: {e}")

except Exception as e:
    print(f"Error: {e}")
