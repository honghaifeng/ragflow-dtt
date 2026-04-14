import mysql.connector
from database import DB_CONFIG


def get_overview_stats():
    """获取概览统计数据"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as cnt FROM organization WHERE status = '1'")
        org_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM user WHERE status = '1'")
        user_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM knowledgebase WHERE status = '1'")
        kb_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(size), 0) as total_size FROM document WHERE status = '1'")
        row = cursor.fetchone()
        file_count = row['cnt']
        total_size = int(row['total_size'])

        cursor.close()
        conn.close()

        return {
            "orgCount": org_count,
            "userCount": user_count,
            "kbCount": kb_count,
            "fileCount": file_count,
            "totalFileSize": total_size,
        }
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return {"orgCount": 0, "userCount": 0, "kbCount": 0, "fileCount": 0, "totalFileSize": 0}
