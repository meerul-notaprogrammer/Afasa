FROM node:20-alpine AS build

ARG VITE_OIDC_ISSUER_URL
ARG VITE_OIDC_CLIENT_ID
ARG VITE_PUBLIC_BASE_URL

WORKDIR /app

COPY services/portal/package*.json ./
RUN npm install

COPY services/portal/ .

ENV VITE_OIDC_ISSUER_URL=$VITE_OIDC_ISSUER_URL
ENV VITE_OIDC_CLIENT_ID=$VITE_OIDC_CLIENT_ID
ENV VITE_PUBLIC_BASE_URL=$VITE_PUBLIC_BASE_URL

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html/portal
COPY services/portal/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
