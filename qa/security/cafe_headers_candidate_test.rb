# frozen_string_literal: true
# Pure Ruby regression tests: no Rails, Docker, PG, uploaded images or network.
require_relative 'cafe_headers_candidate'

def assert(message, value)
  raise "HEADERS CANDIDATE TEST FAIL: #{message}" unless value
end

def header_value(headers, name)
  pair = headers.find { |key, _value| key.to_s.casecmp(name).zero? }
  pair && pair[1]
end

def header_count(headers, name)
  headers.keys.count { |key| key.to_s.casecmp(name).zero? }
end

def wrap(status, headers, body)
  app = ->(_env) { [status, headers, body] }
  CafeHeadersCandidate.new(app)
end

def response_for(app, method = 'GET')
  app.call('REQUEST_METHOD' => method, 'PATH_INFO' => '/')
end

# HTML 200: no enforced CSP, no changes to underlying hash, status or body.
base = { 'Content-Type' => 'text/html; charset=utf-8',
         'Cache-Control' => 'private, max-age=0' }.freeze
body = ['<p>safe synthetic HTML</p>'].freeze
status, headers, returned_body = response_for(wrap(200, base, body))
assert('HTML status', status == 200)
assert('HTML body identity', returned_body.equal?(body))
assert('no original header mutation', base.keys == ['Content-Type', 'Cache-Control'])
assert('nosniff HTML', header_value(headers, 'X-Content-Type-Options') == 'nosniff')
assert('referrer HTML', header_value(headers, 'Referrer-Policy') ==
       'strict-origin-when-cross-origin')
assert('csp report-only HTML', header_value(headers, 'Content-Security-Policy-Report-Only') ==
       CafeHeadersCandidate::CSP_REPORT_ONLY)
assert('does not insert enforced CSP', header_value(headers, 'Content-Security-Policy').nil?)
assert('safe CSP script directive', CafeHeadersCandidate::CSP_REPORT_ONLY.include?("script-src 'self'"))
assert('no unsafe-inline in diagnostic policy',
       !CafeHeadersCandidate::CSP_REPORT_ONLY.include?("'unsafe-inline'"))
assert('Cache-Control unchanged', header_value(headers, 'Cache-Control') == 'private, max-age=0')

# Static media (GET and HEAD): same protective headers, no HTML-only CSP.
jpg = {'Content-Type' => 'image/jpeg', 'Content-Length' => '25'}.freeze
['GET', 'HEAD'].each do |method|
  status, hdr, returned = response_for(wrap(200, jpg, []), method)
  assert("#{method} status", status == 200)
  assert("#{method} nosniff", header_value(hdr, 'X-Content-Type-Options') == 'nosniff')
  assert("#{method} referrer", header_value(hdr, 'Referrer-Policy') ==
         'strict-origin-when-cross-origin')
  assert("#{method} content type", header_value(hdr, 'Content-Type') == 'image/jpeg')
  assert("#{method} body unchanged", returned == [])
  assert("#{method} no CSP", header_value(hdr, 'Content-Security-Policy-Report-Only').nil?)
end

# Respect independently configured policy/header values regardless of case.
existing = {
  'content-type' => 'TEXT/HTML ; charset=UTF-8',
  'x-content-type-options' => 'nosniff',
  'referrer-policy' => 'same-origin',
  'content-security-policy-report-only' => "default-src 'none'",
  'Content-Security-Policy' => "default-src 'self'"
}.freeze
_, hdr, = response_for(wrap(302, existing, ['no change']))
assert('do not override existing nosniff', header_value(hdr, 'x-content-type-options') == 'nosniff')
assert('do not override existing referrer', header_value(hdr, 'referrer-policy') == 'same-origin')
assert('do not override existing report-only',
       header_value(hdr, 'Content-Security-Policy-Report-Only') == "default-src 'none'")
assert('do not override existing enforcing CSP',
       header_value(hdr, 'Content-Security-Policy') == "default-src 'self'")
['X-Content-Type-Options', 'Referrer-Policy', 'Content-Security-Policy-Report-Only'].each do |key|
  assert("no duplicate #{key}", header_count(hdr, key) == 1)
end

# JSON, empty Content-Type and 304 still receive nosniff and referrer, but no CSP.
[{ 'content-type' => 'application/json' },
 { 'Content-Type' => '' },
 {}].each do |case_headers|
  _, hdr, = response_for(wrap(304, case_headers.freeze, []))
  assert('non-HTML nosniff', header_value(hdr, 'X-Content-Type-Options') == 'nosniff')
  assert('non-HTML referrer', header_value(hdr, 'Referrer-Policy') ==
         'strict-origin-when-cross-origin')
  assert('non-HTML no report-only CSP', header_value(hdr, 'Content-Security-Policy-Report-Only').nil?)
end

puts 'CANDIDATE_RACK_HTML_HEADERS_PASS'
puts 'CANDIDATE_RACK_STATIC_IMAGE_GET_HEAD_PASS'
puts 'CANDIDATE_EXISTING_HEADERS_PRESERVED_PASS'
puts 'CANDIDATE_CSP_REPORT_ONLY_NOT_ENFORCED_PASS'
puts 'CANDIDATE_HEADERS_REGRESSION_TESTS_COMPLETE'
