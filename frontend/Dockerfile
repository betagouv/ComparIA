# Railway build for the SvelteKit frontend.
# Build context is the frontend/ directory (mirrors devops/docker/Dockerfile.front).
FROM public.ecr.aws/docker/library/node:24.4 AS builder

WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .
ARG PUBLIC_API_URL MATOMO_ID MATOMO_URL GIT_COMMIT
ENV PUBLIC_API_URL=$PUBLIC_API_URL MATOMO_ID=$MATOMO_ID MATOMO_URL=$MATOMO_URL PUBLIC_GIT_COMMIT=$GIT_COMMIT

RUN yarn build && yarn install --production --ignore-scripts

FROM public.ecr.aws/docker/library/node:24.4-alpine AS runtime
WORKDIR /app

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build

EXPOSE 3000
# adapter-node honours HOST and PORT env vars (set to :: / 3000 on Railway for IPv6 private networking).
CMD ["node", "build"]
