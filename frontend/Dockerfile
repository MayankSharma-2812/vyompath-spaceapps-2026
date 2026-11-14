# ──────────────────────────────────────────────────────────────
# VyomPath Frontend — Production Container Image (Multi-Stage)
# ──────────────────────────────────────────────────────────────
# Stage 1: Build static assets using Node.js
# Stage 2: Serve compiled production bundle through Nginx
# ──────────────────────────────────────────────────────────────

FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ── Runtime Stage: Production Nginx ──────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled frontend from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration (reverse proxies /api to backend)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
