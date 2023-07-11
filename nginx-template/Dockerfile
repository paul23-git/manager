FROM alpine:3.17
RUN apk update
RUN apk upgrade

RUN apk add nginx
RUN apk upgrade

EXPOSE 80 443

VOLUME ["/build_data"]


RUN mkdir /etc/nginx/sites-enabled && \
    mkdir /etc/nginx/sites-available && \
    mkdir /etc/nginx/snippets && \
    mkdir /njs
    
RUN ln -fs /njs /var/www/html

# SSL key
COPY snippets/* /etc/nginx/snippets
COPY *.pem /etc/ssl/certs/
COPY *.key /etc/ssl/private/

# nginx
COPY nginx.conf /etc/nginx/
COPY sites-available/* /etc/nginx/sites-available/
COPY sites-enabled/* /etc/nginx/sites-enabled/

ENTRYPOINT ["nginx", "-g", "daemon off;"]

COPY javascript/build /njs





