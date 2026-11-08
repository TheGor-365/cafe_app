#!/usr/bin/env bash
# Disposable GitHub CI upgrade to Rails 7.0; never owner-local.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == "true" && "$CI" == "true" &&
   -n "$GITHUB_WORKSPACE" && "$PWD" == "$GITHUB_WORKSPACE" ]] || {
  echo "CAFE RAILS70 STOP: disposable GitHub workspace required" >&2; exit 12;
}
git config --global --add safe.directory "$GITHUB_WORKSPACE"
[[ -z "$(git status --porcelain)" ]] || {
  echo "CAFE RAILS70 STOP: checkout not pristine" >&2; exit 13;
}
ruby -v | grep -F 'ruby 2.7.8' >/dev/null
grep -Fx "ruby '2.7.8'" Gemfile >/dev/null
grep -Fx "gem 'rails', '~> 6.1.7', '>= 6.1.7.10'" Gemfile >/dev/null
grep -Fx '    rails (6.1.7.10)' Gemfile.lock >/dev/null
grep -Fx "gem 'logger', '= 1.4.2'" Gemfile >/dev/null

# Rails 7.0.10 is an unsupported migration step. Sprockets was removed
# from Rails' default gem dependencies in Rails7, so retain it explicitly.
sed -i "s/gem 'rails', '~> 6.1.7', '>= 6.1.7.10'/gem 'rails', '~> 7.0.10', '>= 7.0.10'/" Gemfile
echo "gem 'sprockets-rails', '~> 3.4'" >> Gemfile
# The old 2021 Devise Git revision calls AS::Dependencies.reference,
# removed by Rails 7. Devise 5.0.4 has both Rails7 support and 2026
# security patches. Only change the disposable CI Gemfile.
grep -Fx "gem 'devise', github: 'heartcombo/devise', branch: 'ca-omniauth-2'" Gemfile >/dev/null
sed -i "s/gem 'devise', github: 'heartcombo\/devise', branch: 'ca-omniauth-2'/gem 'devise', '= 5.0.4'/" Gemfile
grep -Fx "gem 'devise', '= 5.0.4'" Gemfile >/dev/null
gem install bundler -v 2.2.13 --no-document
bundle _2.2.13_ update rails sprockets-rails devise
bundle _2.2.13_ lock --add-platform x86_64-linux
bundle _2.2.13_ exec ruby -e '
  require "rails"
  abort "not Rails 7.0" unless Rails.version == "7.0.10"
  puts "CAFE RAILS70 GEM PASS #{RUBY_VERSION}/#{Rails.version}"
'
mkdir -p rails70-artifact
cp Gemfile Gemfile.lock rails70-artifact/
echo "CAFE RAILS70 CI DEPENDENCY RESOLUTION PASS"
