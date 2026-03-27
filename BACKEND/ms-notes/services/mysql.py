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
        CREATE TABLE IF NOT EXISTS notes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            etudiant_username VARCHAR(100) NOT NULL,
            matiere VARCHAR(100) NOT NULL,
            type ENUM('examen', 'controle', 'moyenne') NOT NULL,
            note DECIMAL(5,2) NOT NULL,
            coefficient DECIMAL(3,1) DEFAULT 1.0,
            semestre VARCHAR(20),
            annee_universitaire VARCHAR(20),
            commentaire TEXT,
            saisi_par VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def create_note(etudiant_username, matiere, type_note, note,
                coefficient, semestre, annee_universitaire,
                commentaire, saisi_par) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO notes 
        (etudiant_username, matiere, type, note, coefficient, semestre, annee_universitaire, commentaire, saisi_par)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (etudiant_username, matiere, type_note, note, coefficient,
         semestre, annee_universitaire, commentaire, saisi_par)
    )
    conn.commit()
    note_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return note_id


def get_notes_by_etudiant(etudiant_username: str, matiere: str = None,
                           type_note: str = None, semestre: str = None) -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM notes WHERE etudiant_username = %s"
    params = [etudiant_username]

    if matiere:
        query += " AND matiere = %s"
        params.append(matiere)
    if type_note:
        query += " AND type = %s"
        params.append(type_note)
    if semestre:
        query += " AND semestre = %s"
        params.append(semestre)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_all_notes(matiere: str = None, type_note: str = None,
                  semestre: str = None) -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if matiere:
        query += " AND matiere = %s"
        params.append(matiere)
    if type_note:
        query += " AND type = %s"
        params.append(type_note)
    if semestre:
        query += " AND semestre = %s"
        params.append(semestre)

    query += " ORDER BY etudiant_username, matiere"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_note_by_id(note_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notes WHERE id = %s", (note_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def update_note(note_id: int, fields: dict) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = %s" for k in fields.keys()])
    values = list(fields.values()) + [note_id]
    cursor.execute(f"UPDATE notes SET {set_clause} WHERE id = %s", values)
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return affected > 0


def delete_note(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return affected > 0


def get_moyenne_etudiant(etudiant_username: str, semestre: str = None) -> list:
    """Calcule la moyenne par matière pour un étudiant"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT matiere, 
               ROUND(SUM(note * coefficient) / SUM(coefficient), 2) as moyenne,
               COUNT(*) as nb_notes,
               semestre
        FROM notes 
        WHERE etudiant_username = %s AND type != 'moyenne'
    """
    params = [etudiant_username]

    if semestre:
        query += " AND semestre = %s"
        params.append(semestre)

    query += " GROUP BY matiere, semestre ORDER BY matiere"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result