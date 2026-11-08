# frozen_string_literal: true

# Deliberately NOT mounted into the existing cafe_app Rails middleware stack.
# A separately reviewed QA-only Rails candidate can mount this first (outermost)
# so ActionDispatch::Static /uploads responses also traverse the wrapper.
#
# No cookies, bodies, private paths, or violation reports are inspected/stored.
class CafeHeadersCandidate
  # Diagnostic policy ONLY. There is no report-to/report-uri collector.
  # Browser DevTools checks and an approved private reporting plan are still
  # required before claiming that CSP violations have been measured.
  CSP_REPORT_ONLY = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "form-action 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' ws: wss:"
  ].join('; ').freeze

  def initialize(app)
    @app = app
  end

  def call(env)
    status, response_headers, body = @app.call(env)

    # Avoid mutating a shared, possibly frozen header hash supplied by another
    # middleware; preserve status, body, MIME, caching and existing CSP.
    headers = response_headers.dup
    set_unless_present(headers, 'X-Content-Type-Options', 'nosniff')
    set_unless_present(headers, 'Referrer-Policy', 'strict-origin-when-cross-origin')

    content_type = get_header(headers, 'Content-Type').to_s
    if content_type.split(';', 2).first.to_s.strip.downcase == 'text/html'
      set_unless_present(headers, 'Content-Security-Policy-Report-Only',
                         CSP_REPORT_ONLY)
    end

    [status, headers, body]
  end

  private

  def get_header(headers, name)
    key = headers.keys.find { |candidate| candidate.to_s.casecmp(name).zero? }
    key && headers[key]
  end

  def set_unless_present(headers, name, value)
    exists = headers.keys.any? do |key|
      key.to_s.casecmp(name).zero?
    end
    headers[name] = value unless exists
  end
end
