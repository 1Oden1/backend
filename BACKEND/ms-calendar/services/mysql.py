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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evenements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titre VARCHAR(255) NOT NULL,
            description TEXT,
            type ENUM('cours', 'examen', 'evenement') NOT NULL,
            date_debut DATETIME NOT NULL,
            date_fin DATETIME NOT NULL,
            lieu VARCHAR(255),
            filiere VARCHAR(100),
            niveau VARCHAR(50),
            cree_par VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def create_evenement(titre, description, type_evt, date_debut,
                     date_fin, lieu, filiere, niveau, cree_par) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO evenements 
        (titre, description, type, date_debut, date_fin, lieu, filiere, niveau, cree_par)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (titre, description, type_evt, date_debut, date_fin, lieu, filiere, niveau, cree_par)
    )
    conn.commit()
    evt_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return evt_id


def get_all_evenements(type_evt=None, niveau=None, filiere=None) -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM evenements WHERE 1=1"
    params = []

    if type_evt:
        query += " AND type = %s"
        params.append(type_evt)
    if niveau:
        query += " AND niveau = %s"
        params.append(niveau)
    if filiere:
        query += " AND filiere = %s"
        params.append(filiere)

    query += " ORDER BY date_debut ASC"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_evenement_by_id(evt_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM evenements WHERE id = %s", (evt_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def update_evenement(evt_id: int, fields: dict) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    set_clause = ", ".join([f"{k} = %s" for k in fields.keys()])
    values = list(fields.values()) + [evt_id]

    cursor.execute(f"UPDATE evenements SET {set_clause} WHERE id = %s", values)
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return affected > 0


def delete_evenement(evt_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evenements WHERE id = %s", (evt_id,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return affected > 0