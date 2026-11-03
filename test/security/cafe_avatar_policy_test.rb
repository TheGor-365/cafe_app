# frozen_string_literal: true

require 'minitest/autorun'
require 'tempfile'
require 'carrierwave'
require_relative '../../qa/security/avatar_uploader'

class CafeAvatarPolicyTest < Minitest::Test
  FakeFile = Struct.new(:path, :original_filename)

  class UploaderHarness < AvatarUploader
    attr_accessor :fake_file

    def file
      fake_file
    end
  end

  def with_upload(bytes, filename)
    sample = Tempfile.new(['cafe-avatar-policy-', '.upload'])
    sample.binmode
    sample.write(bytes)
    sample.flush

    uploader = UploaderHarness.new
    uploader.fake_file = FakeFile.new(sample.path, filename)
    yield uploader
  ensure
    sample.close! if sample
  end

  def test_fixed_allowlist_and_size
    uploader = UploaderHarness.new
    assert_equal %w(jpg jpeg png gif), uploader.extension_allowlist
    allowlist = uploader.content_type_allowlist
    assert_equal 1, allowlist.length
    %w(image/png image/jpeg image/gif).each do |mime|
      assert_match allowlist.first, mime
    end
    %w(image/svg+xml text/html application/xhtml+xml image/png,text/html).each do |mime|
      refute_match allowlist.first, mime
    end
    assert_equal 1..(2 * 1024 * 1024), uploader.size_range
  end

  def test_accepts_matching_image_signatures
    {
      'avatar.png' => "\x89PNG\r\n\x1A\n".b + ("\x00".b * 8),
      'avatar.jpg' => "\xFF\xD8\xFF".b + ("\x00".b * 13),
      'avatar.jpeg' => "\xFF\xD8\xFF".b + ("\x00".b * 13),
      'avatar.gif' => "GIF89a".b + ("\x00".b * 10)
    }.each do |name, bytes|
      with_upload(bytes, name) do |uploader|
        assert_nil uploader.verify_image_bytes!, name
      end
    end
  end

  def test_rejects_spoofed_or_unrecognized_uploads
    samples = [
      ['<svg><script>alert(1)</script></svg>', 'avatar.png'],
      ['<html><script>alert(1)</script></html>', 'avatar.jpg'],
      ["\x89PNG\r\n\x1A\n".b + 'ignored', 'avatar.svg'],
      ["\x89PNG\r\n\x1A\n".b + 'ignored', 'avatar.jpg'],
      ["\xFF\xD8\xFF".b + 'ignored', 'avatar.gif'],
      ['GIF89a' + 'ignored', 'avatar.png'],
      ['not an image', 'avatar.jpg'],
      ['some data', '../avatar.png'],
      ['', 'avatar.png']
    ]
    samples.each do |bytes, name|
      with_upload(bytes, name) do |uploader|
        assert_raises(CarrierWave::IntegrityError, name) do
          uploader.verify_image_bytes!
        end
      end
    end
  end

  def test_rejects_oversized_file_even_with_matching_png_header
    oversized = "\x89PNG\r\n\x1A\n".b + ("\x00".b * (2 * 1024 * 1024))
    with_upload(oversized, 'avatar.png') do |uploader|
      assert_raises(CarrierWave::IntegrityError) do
        uploader.verify_image_bytes!
      end
    end
  end
end
