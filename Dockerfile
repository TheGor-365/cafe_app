# Isolated pre-release preview. Ruby 2.7 / Rails 6.1 remain EOL; no direct public HTTP domain.
FROM node:14-bullseye-slim AS node
FROM ruby:2.7.8-bullseye
RUN apt-get update -qq && apt-get install -y --no-install-recommends git libpq-dev libmagickwand-dev imagemagick ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN npm install -g yarn@1.22.22
WORKDIR /app
ENV RAILS_ENV=production RAILS_SERVE_STATIC_FILES=true RAILS_LOG_TO_STDOUT=true BUNDLE_WITHOUT=development:test
COPY Gemfile Gemfile.lock ./
RUN gem install bundler -v 2.2.13 --no-document && bundle _2.2.13_ config set deployment true && bundle _2.2.13_ install --jobs 4 --retry 3
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive
COPY . .
# Build-only dummy secret; real SECRET_KEY_BASE is provided through Railway at runtime.
RUN SECRET_KEY_BASE=39e0aee9fd14c394b6905d59b7f13996d3301aae9574a839f8ea8a2e85ae1b52 bundle _2.2.13_ exec rails assets:precompile
EXPOSE 3000
CMD ["sh", "-lc", "bundle _2.2.13_ exec puma -C config/puma.rb"]
