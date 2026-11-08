# Isolated pre-release preview. Ruby 2.7 / Rails 6.1 remain EOL; no direct public HTTP domain.
FROM node:14-bullseye-slim AS node
FROM ruby:2.7.8-bullseye
# Ruby 2.7 buildpack-deps base already ships build tools and git.\n# Avoid unavailable EOL Bullseye APT mirrors during isolated preview build.\n# ImageMagick upload processing remains unverified for release.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN node /usr/local/lib/node_modules/npm/bin/npm-cli.js install -g yarn@1.22.22
WORKDIR /app
ENV RAILS_ENV=production RAILS_SERVE_STATIC_FILES=true RAILS_LOG_TO_STDOUT=true BUNDLE_WITHOUT=development:test RUBYOPT=-rlogger
COPY Gemfile Gemfile.lock ./
RUN gem install bundler -v 2.2.13 --no-document && bundle _2.2.13_ config set deployment true && bundle _2.2.13_ install --jobs 4 --retry 3
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive
COPY . .
RUN mkdir -p tmp/pids tmp/cache
# Build-only dummy secret and localhost-only DB URI (no database is provisioned in build).\n# Real SECRET_KEY_BASE and DATABASE_URL are Railway runtime variables.
RUN SECRET_KEY_BASE=39e0aee9fd14c394b6905d59b7f13996d3301aae9574a839f8ea8a2e85ae1b52 DATABASE_URL=postgresql://build:build@127.0.0.1:5432/cafe_build_assets_only bundle _2.2.13_ exec rails assets:precompile
EXPOSE 3000
CMD ["sh", "-lc", "bundle _2.2.13_ exec puma -C config/puma.rb"]
