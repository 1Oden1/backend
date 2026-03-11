FROM nginx:alpine

LABEL maintainer="EST Salé – ENT"
LABEL description="Frontend ENT – Interfaces statiques (login, admin, étudiant, enseignant)"

# Supprimer la config par défaut
RUN rm /etc/nginx/conf.d/default.conf

# Config Nginx
COPY nginx.conf /etc/nginx/conf.d/ent-frontend.conf

# ── Fichiers communs ──────────────────────────
# (styles globaux, utilitaires JS partagés entre toutes les interfaces)
# COPY shared/ /usr/share/nginx/html/shared/

# ── Interface Login ───────────────────────────
COPY login/index.html  /usr/share/nginx/html/login/index.html
COPY login/style.css   /usr/share/nginx/html/login/style.css
COPY login/auth.js     /usr/share/nginx/html/login/auth.js

# ── Interface Admin ───────────────────────────
# (décommenter quand les fichiers seront prêts)
# COPY admin/index.html  /usr/share/nginx/html/admin/index.html
# COPY admin/style.css   /usr/share/nginx/html/admin/style.css
# COPY admin/admin.js    /usr/share/nginx/html/admin/admin.js

# ── Interface Étudiant ────────────────────────
# COPY etudiant/index.html  /usr/share/nginx/html/etudiant/index.html
# COPY etudiant/style.css   /usr/share/nginx/html/etudiant/style.css
# COPY etudiant/etudiant.js /usr/share/nginx/html/etudiant/etudiant.js

# ── Interface Enseignant ──────────────────────
# COPY enseignant/index.html  /usr/share/nginx/html/enseignant/index.html
# COPY enseignant/style.css   /usr/share/nginx/html/enseignant/style.css
# COPY enseignant/enseignant.js /usr/share/nginx/html/enseignant/enseignant.js

# Rediriger la racine vers /login/
RUN echo '<html><head><meta http-equiv="refresh" content="0;url=/login/"></head></html>' \
    > /usr/share/nginx/html/index.html

RUN chmod -R 755 /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
