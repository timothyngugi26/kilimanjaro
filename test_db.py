import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="food_ordering",
        user="food_user",
        password="Godhasincreasedme700%"
    )
    print("✅ Database connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")