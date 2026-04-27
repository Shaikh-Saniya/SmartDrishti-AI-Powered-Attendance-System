import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/attendance_db"
engine = create_async_engine(DATABASE_URL)

async def main():
    async with engine.connect() as conn:
        try:
            # 1. Fetch one actual embedding string from an ACTIVE student
            get_emb = await conn.execute(text("""
                SELECT e.embedding::text 
                FROM embeddings e
                JOIN students s ON e.student_id = s.id
                WHERE s.is_active = true
                LIMIT 1;
            """))
            query_vector_str = get_emb.scalar()
            
            if not query_vector_str:
                print("No active student embeddings found in DB.")
                return

            # 2. Run the manual similarity query
            manual_query = text(f"""
                SELECT e.student_id, 
                       1 - (e.embedding <=> '{query_vector_str}'::vector) AS similarity
                FROM embeddings e
                JOIN students s ON e.student_id = s.id AND s.is_active = true
                ORDER BY e.embedding <=> '{query_vector_str}'::vector ASC
                LIMIT 1;
            """)
            
            res = await conn.execute(manual_query)
            row = res.first()
            
            if row:
                result = {
                    "query_vector_used": query_vector_str[:50] + "...",
                    "student_id": str(row[0]),
                    "similarity": float(row[1])
                }
            else:
                result = "No matches found."

            print(json.dumps(result, indent=2))

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
