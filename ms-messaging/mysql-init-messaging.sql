-- ════════════════════════════════════════════════════════════════════════════
-- Ajout de la base ent_messaging (à ajouter dans mysql-init.sql existant)
-- ════════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS `ent_messaging`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON `ent_messaging`.* TO 'ent_user'@'%';

FLUSH PRIVILEGES;

-- Note : Le keyspace Cassandra `ent_messaging` est créé automatiquement
-- au démarrage du container ms-messaging (via init_cassandra()).

-- ════════════════════════════════════════════════════════════════════════════
-- Rôle Keycloak à ajouter manuellement dans realm-export.json
-- ════════════════════════════════════════════════════════════════════════════
-- Ajouter dans le tableau "roles.realm" de ms-auth/keycloak/realm-export.json :
--
-- {
--   "id": "delegue",
--   "name": "delegue",
--   "description": "Délégué de filière — peut discuter avec les enseignants de sa filière",
--   "composite": false,
--   "clientRole": false,
--   "containerId": "ent-sale"
-- }
--
-- Un délégué est un étudiant avec les rôles Keycloak : "etudiant" + "delegue"
-- Son filiere_id est résolu via ent_notes.etudiants (user_id = Keycloak sub)
-- ════════════════════════════════════════════════════════════════════════════
