FROM python:3.11-slim AS backend-builder

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json .
RUN npm install

COPY frontend/ .
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y nginx certbot python3-certbot-nginx && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /app/backend /app/backend
COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/package*.json /app/frontend/
COPY --from=frontend-builder /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

COPY nginx.conf /etc/nginx/nginx.conf

COPY start-docker.sh /app/start-docker.sh
RUN chmod +x /app/start-docker.sh

EXPOSE 80 443

CMD ["/app/start-docker.sh"]
