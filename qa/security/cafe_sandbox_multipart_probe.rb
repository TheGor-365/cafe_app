# frozen_string_literal: true
# True multipart-over-HTTP QA probes; run ONLY via Rails runner INSIDE isolated sandbox.
# No external hosts/ports, no browser login, no production/QA DB writes.
require 'net/http'
require 'nokogiri'
require 'securerandom'
require 'digest'
require 'tmpdir'
require 'fileutils'
require 'uri'

SANDBOX_CLUSTER = ENV.fetch('EXPECTED_SANDBOX_CLUSTER')
actual_cluster = ActiveRecord::Base.connection.select_value(
  'SELECT system_identifier::text FROM pg_control_system()'
).to_s
raise 'STOP: wrong sandbox database' unless actual_cluster == SANDBOX_CLUSTER

network = ENV.fetch('DATABASE_URL')
raise 'STOP: wrong database URL' unless
  network == 'postgresql://postgres@cafe-app-db:5432/cafe'

gem_version = Gem.loaded_specs.fetch('carrierwave').version.to_s
raise 'STOP: CarrierWave not patched' unless gem_version == '2.2.7'

STORE = '/app/public/uploads'
raise 'STOP: missing sandbox media mount' unless File.directory?(STORE)
before_users = User.count

def files_snapshot
  Dir.glob(File.join(STORE, '**', '*'), File::FNM_DOTMATCH).sort.each_with_object({}) do |path, memo|
    next unless File.file?(path)
    memo[path.sub(STORE + '/', '')] = Digest::SHA256.file(path).hexdigest
  end
end

baseline_files = files_snapshot
raise 'STOP: expected restored media baseline not 10 files' unless
  baseline_files.size == 10

class QaMultipartClient
  def initialize
    @cookies = {}
  end

  def perform(request)
    unless @cookies.empty?
      request['Cookie'] = @cookies.map { |key, value| "#{key}=#{value}" }.join('; ')
    end
    request['Host'] = '127.0.0.1:3001'
    http = Net::HTTP.new('127.0.0.1', 3001, nil)
    http.open_timeout = 3
    http.read_timeout = 18
    response = http.request(request)
    (response.get_fields('Set-Cookie') || []).each do |item|
      key, value = item.split(';', 2).first.split('=', 2)
      @cookies[key] = value if key && value
    end
    response
  end

  def get(path)
    perform(Net::HTTP::Get.new(path))
  end

  def registration_token!
    page = get('/users/sign_up')
    raise "GET signup HTTP #{page.code}" unless page.code == '200'
    parsed = Nokogiri::HTML(page.body)
    form = parsed.at_css('form[action="/users"]')
    raise 'registration multipart form absent' unless
      form && form['enctype'] == 'multipart/form-data'
    token = form.at_css('input[name="authenticity_token"]')&.[]('value') ||
            parsed.at_css('meta[name="csrf-token"]')&.[]('content')
    raise 'authenticity token absent' if token.nil? || token.empty?
    token
  end

  def signup(username:, email:, password:, avatar_bytes:, filename:, mime:)
    token = registration_token!
    fields = {
      'authenticity_token' => token,
      'user[username]' => username,
      'user[email]' => email,
      'user[password]' => password,
      'user[password_confirmation]' => password
    }
    boundary = "----cafe-qa-#{SecureRandom.hex(12)}"
    body = ''.b
    fields.each do |name, value|
      body << "--#{boundary}\r\n".b
      body << "Content-Disposition: form-data; name=\"#{name}\"\r\n\r\n".b
      body << value.to_s.b
      body << "\r\n".b
    end
    body << "--#{boundary}\r\n".b
    body << "Content-Disposition: form-data; name=\"user[avatar]\"; filename=\"#{filename}\"\r\n".b
    body << "Content-Type: #{mime}\r\n\r\n".b
    body << avatar_bytes.b
    body << "\r\n--#{boundary}--\r\n".b

    request = Net::HTTP::Post.new('/users')
    request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
    request['Origin'] = 'http://127.0.0.1:3001'
    request.body = body
    perform(request)
  end
end

valid = {}
invalid = []
created_emails = []
results = []

begin
  Dir.mktmpdir('cafe-sandbox-http-', '/tmp') do |tmpdir|
    %w(png jpg gif).each do |ext|
      file = File.join(tmpdir, "valid.#{ext}")
      ok = system('convert', '-size', '9x9', 'xc:#336699', file,
                  out: File::NULL, err: File::NULL)
      raise "ImageMagick could not build tiny #{ext} fixture" unless ok
      valid[ext] = File.binread(file)
      raise "empty image fixture #{ext}" if valid[ext].empty?
    end

    invalid = [
      ['html_as_jpeg', '<script>alert(1)</script>'.b, 'attack.jpg', 'image/jpeg'],
      ['svg_upload', '<svg xmlns="http://www.w3.org/2000/svg"/>'.b,
       'vector.svg', 'image/svg+xml'],
      ['mismatched_magic', valid.fetch('png'), 'mismatch.jpg', 'image/jpeg'],
      ['oversize_jpeg', "\xFF\xD8\xFF".b + ('A'.b * (2 * 1024 * 1024)),
       'large.jpg', 'image/jpeg'],
      ['empty_image', ''.b, 'empty.png', 'image/png'],
      ['truncated_jpeg', "\xFF\xD8\xFF".b, 'broken.jpg', 'image/jpeg'],
      ['wrong_declared_mime', valid.fetch('png'), 'declared.png', 'text/plain']
    ]

    invalid.each do |name, payload, filename, mime|
      client = QaMultipartClient.new
      suffix = SecureRandom.hex(7)
      email = "reject-#{suffix}@example.test"
      created_emails << email
      old_count = User.count
      response = client.signup(
        username: "reject_#{suffix}", email: email,
        password: SecureRandom.hex(18),
        avatar_bytes: payload, filename: filename, mime: mime
      )
      record = User.find_by(email: email)
      unless record.nil? && User.count == old_count &&
             %w(200 400 415 422).include?(response.code)
        raise "SECURITY FAIL #{name}: HTTP #{response.code}; persisted=#{!record.nil?}"
      end
      results << "REJECT #{name}: HTTP #{response.code} / no user"
    end

    [['png', 'image/png'], ['jpg', 'image/jpeg'],
     ['gif', 'image/gif']].each do |ext, mime|
      client = QaMultipartClient.new
      suffix = SecureRandom.hex(7)
      email = "accept-#{suffix}@example.test"
      created_emails << email
      old_count = User.count
      response = client.signup(
        username: "accept_#{suffix}", email: email,
        password: SecureRandom.hex(18),
        avatar_bytes: valid.fetch(ext), filename: "valid.#{ext}", mime: mime
      )
      user = User.find_by(email: email)
      unless user && User.count == old_count + 1 &&
             %w(302 303).include?(response.code)
        raise "VALID IMAGE FAIL #{ext}: HTTP #{response.code}; persisted=#{!user.nil?}"
      end
      avatar = user.avatar.path
      thumb = user.avatar.thumb.path
      unless avatar && thumb && File.file?(avatar) && File.file?(thumb) &&
             File.realpath(avatar).start_with?(STORE + '/user/avatar/') &&
             File.realpath(thumb).start_with?(STORE + '/user/avatar/')
        raise "VALID IMAGE FAIL #{ext}: avatar/thumbnail not stored inside sandbox"
      end
      profile = client.get('/account')
      raise "VALID IMAGE FAIL #{ext}: login HTTP #{profile.code}" unless
        profile.code == '200'
      results << "ACCEPT #{ext}: HTTP #{response.code} / DB + avatar + thumbnail / authenticated"
    end
  end
ensure
  # All emails generated randomly by this isolated test, not existing accounts.
  # Cleanup only these disposable records; CarrierWave deletes their media.
  created_emails.each do |email|
    record = User.find_by(email: email)
    record.destroy! if record
  end
end

raise 'QA disposable user cleanup mismatch' unless User.count == before_users
raise 'QA media differs from restored baseline after cleanup' unless
  files_snapshot == baseline_files

results.each { |message| puts message }
puts 'SANDBOX USER/THUMBNAIL CLEANUP PASS'
puts 'SANDBOX REAL HTTP MULTIPART SECURITY PASS'
