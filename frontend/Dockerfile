FROM nginx:1.25-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY nginx.conf /etc/nginx/nginx.conf

COPY login/      /usr/share/nginx/html/login/
COPY admin/      /usr/share/nginx/html/admin/
COPY etudiant/   /usr/share/nginx/html/etudiant/
COPY enseignant/ /usr/share/nginx/html/enseignant/

# Redirect root to login
RUN echo '<html><head><meta http-equiv="refresh" content="0;url=/login/"></head></html>' \
    > /usr/share/nginx/html/index.html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
