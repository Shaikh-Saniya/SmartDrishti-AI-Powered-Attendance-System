"""One-shot migration: replace global roll_number unique constraint with composite (roll_number, class)."""

import psycopg2

DATABASE_URL = "host=localhost port=5432 dbname=attendance_db user=postgres password=password"


def run():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        print("Dropping old global constraint (if exists)...")
        cur.execute("ALTER TABLE students DROP CONSTRAINT IF EXISTS students_roll_number_key;")
        print("  Done.")

        print("Dropping existing composite constraint (if exists)...")
        cur.execute("ALTER TABLE students DROP CONSTRAINT IF EXISTS uq_student_roll_class;")
        print("  Done.")

        print("Adding new composite unique constraint (roll_number, class)...")
        cur.execute(
            "ALTER TABLE students ADD CONSTRAINT uq_student_roll_class UNIQUE (roll_number, class);"
        )
        print("  Done.")

        print("\nMigration complete. Current unique constraints on 'students':")
        cur.execute(
            """
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'students'::regclass AND contype = 'u';
            """
        )
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
