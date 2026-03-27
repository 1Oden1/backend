import mysql.connector
from mysql.connector import Error
from config import settings


def get_connection():
    try:
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB
        )
        return conn
    except Error as e:
        raise Exception(f"Erreur connexion MySQL: {e}")


def get_all_cours() -> list:
    """Récupère tous les cours"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cours ORDER BY created_at DESC")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_cours_by_id(cours_id: int) -> dict:
    """Récupère un cours par ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cours WHERE id = %s", (cours_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def search_cours(matiere: str = None, niveau: str = None) -> list:
    """Recherche des cours par matière et/ou niveau"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM cours WHERE 1=1"
    params = []

    if matiere:
        query += " AND matiere = %s"
        params.append(matiere)
    if niveau:
        query += " AND niveau = %s"
        params.append(niveau)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result