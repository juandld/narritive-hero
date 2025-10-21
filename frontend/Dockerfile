# build stage
FROM node:18-alpine as build

WORKDIR /app

ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# production stage
FROM nginx:stable-alpine as production

# replace default nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
