# Frontend Dockerfile
FROM node:20-slim AS build

WORKDIR /app

COPY web-react/package*.json ./
RUN npm install

COPY web-react/ .

# Use build-time ARG to set the API URL
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Serving with Nginx
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config to handle SPA routing if needed
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
