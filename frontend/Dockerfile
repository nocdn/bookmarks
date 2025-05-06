# stage 1: build svelte+vite app w/ bun
FROM oven/bun:alpine AS builder
WORKDIR /app
COPY package.json bun.lock package-lock.json ./
RUN bun install
COPY . .
RUN bun run build

# stage 2: serve app w/ caddy
FROM caddy:latest
# copy caddyfile
COPY Caddyfile /etc/caddy/Caddyfile
# copy built app to caddy html dir
COPY --from=builder /app/dist /usr/share/caddy/html
# expose caddy port
EXPOSE 6731