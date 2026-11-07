#!/usr/bin/env bash
# CI ONLY: mutates Gemfile/Gemfile.lock on a disposable GitHub Actions runner.
# Never run on owner-local working trees, Docker or databases.
set -euo pipefail
if [[ "$GITHUB_ACTIONS" != "true" || "$CI" != "true" ||
      -z "$GITHUB_WORKSPACE" || "$PWD" != "$GITHUB_WORKSPACE" ]]; then
  echo "CAFE BRIDGE STOP: GitHub Actions isolated workspace required" >&2
  exit 12
fi
# Actions checkout may be owned by a different UID inside ruby:2.7.8.
# Mark only the exact ephemeral workspace safe for Git inspection.
git config --global --add safe.directory "$GITHUB_WORKSPACE"
case "$1" in
  ruby27_rails60|ruby27_rails61) scenario="$1" ;;
  *) echo "CAFE BRIDGE STOP: unknown scenario" >&2; exit 13 ;;
esac
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "CAFE BRIDGE STOP: Git checkout not pristine" >&2
  exit 14
fi
ruby -v | grep -F 'ruby 2.7.8' >/dev/null
grep -Fx "ruby '2.5.8'" Gemfile >/dev/null
grep -Fx "gem 'rails', '~> 6.0.3', '>= 6.0.3.6'" Gemfile >/dev/null

sed -i "s/ruby '2.5.8'/ruby '2.7.8'/" Gemfile
if [[ "$scenario" == "ruby27_rails61" ]]; then
  sed -i "s/gem 'rails', '~> 6.0.3', '>= 6.0.3.6'/gem 'rails', '~> 6.1.7', '>= 6.1.7.10'/" Gemfile
fi
grep -Fx "ruby '2.7.8'" Gemfile >/dev/null
if [[ "$scenario" == "ruby27_rails61" ]]; then
  grep -Fx "gem 'rails', '~> 6.1.7', '>= 6.1.7.10'" Gemfile >/dev/null
fi

# Rails 6.1 dependency resolution selects logger 1.7 while Ruby 2.7
# preloads the 1.4.2 default gem via RUBYOPT=-rlogger. Avoid double
# activation in this isolated Rails 6.1 CI scenario (not owner runtime).
if [[ "$scenario" == "ruby27_rails61" ]]; then
  [[ -n "$GITHUB_ENV" ]] || { echo "Missing Actions environment file" >&2; exit 16; }
  export RUBYOPT=""
  printf 'RUBYOPT=\\n' >> "$GITHUB_ENV"
fi

gem install bundler -v 2.2.13 --no-document
# Bundler 2.2.13 has no --ruby switch on 'bundle lock'. Update the
# exact pre-existing Ruby version line inside the disposable lockfile.
sed -i 's/ruby 2\.5\.8p224/ruby 2.7.8p225/' Gemfile.lock
if [[ "$scenario" == "ruby27_rails61" ]]; then
  # Rails 6.0 lock pins actionpack/railties to 6.0.3.6. A generic
  # lock resolution would fail before dependency updates can run.
  bundle _2.2.13_ update rails
  bundle _2.2.13_ lock --add-platform x86_64-linux
else
  bundle _2.2.13_ lock --add-platform x86_64-linux
  bundle _2.2.13_ install --jobs 2 --retry 2
fi
mkdir -p "bridge-artifacts/$scenario"
cp Gemfile "bridge-artifacts/$scenario/Gemfile"
cp Gemfile.lock "bridge-artifacts/$scenario/Gemfile.lock"
if [[ "$scenario" == "ruby27_rails61" ]]; then rails_prefix="6.1."; else rails_prefix="6.0."; fi
bundle _2.2.13_ exec ruby -e '
  require "rails"
  prefix = ARGV.fetch(0)
  raise "Unexpected Rails version" unless Rails.version.start_with?(prefix)
  puts "CAFE BRIDGE RUBY/RAILS VERSIONS PASS: #{RUBY_VERSION} / #{Rails.version}"
' "$rails_prefix"
echo "CAFE BRIDGE DEPENDENCY RESOLUTION PASS: $scenario"
