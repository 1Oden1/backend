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


def init_db():
    """Crée les tables si elles n'existent pas"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cours (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titre VARCHAR(255) NOT NULL,
            description TEXT,
            matiere VARCHAR(100),
            niveau VARCHAR(50),
            enseignant VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def create_cours(titre: str, description: str, matiere: str,
                 niveau: str, enseignant: str) -> int:
    """Crée un cours dans MySQL et retourne son ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO cours (titre, description, matiere, niveau, enseignant) VALUES (%s, %s, %s, %s, %s)",
        (titre, description, matiere, niveau, enseignant)
    )
    conn.commit()
    cours_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return cours_id


def get_all_cours() -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cours ORDER BY created_at DESC")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_cours_by_id(cours_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cours WHERE id = %s", (cours_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result