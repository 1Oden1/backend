-- Créé automatiquement au premier démarrage de MySQL
-- Toutes les bases de données de l'ENT sont initialisées ici

CREATE DATABASE IF NOT EXISTS `keycloak`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `ent_calendar`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `ent_notes`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Accorder tous les droits à ent_user sur toutes les bases
GRANT ALL PRIVILEGES ON `keycloak`.*     TO 'ent_user'@'%';
GRANT ALL PRIVILEGES ON `ent_calendar`.* TO 'ent_user'@'%';
GRANT ALL PRIVILEGES ON `ent_notes`.*    TO 'ent_user'@'%';

FLUSH PRIVILEGES;
