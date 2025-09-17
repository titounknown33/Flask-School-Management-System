import sqlite3

def alter_payments_table():
    conn = sqlite3.connect('school.db')
    try:
        conn.execute("ALTER TABLE payments ADD COLUMN discount REAL DEFAULT 0.15")
    except Exception as e:
        print("discount column:", e)
    try:
        conn.execute("ALTER TABLE payments ADD COLUMN khr_rate INTEGER DEFAULT 4100")
    except Exception as e:
        print("khr_rate column:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_payments_table()
    print("Done.")