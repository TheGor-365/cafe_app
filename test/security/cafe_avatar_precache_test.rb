# frozen_string_literal: true
# Unit/integration gate for QA-only pre-cache upload policy. Decoder mocked
# deliberately in CI; real ImageMagick decoding is required in owner sandbox.
require 'minitest/autorun'
require 'minitest/mock'
require 'carrierwave'
require 'mini_magick'
require 'tmpdir'
require 'fileutils'
require_relative '../../qa/security/avatar_uploader_preflight'

class CafeAvatarPrecacheTest < Minitest::Test
  class UploadedFile
    attr_reader :path, :original_filename, :content_type
    def initialize(path, name, type)
      @path = path
      @original_filename = name
      @content_type = type
      @io = File.open(path, 'rb')
    end

    def read(*args)
      @io.read(*args)
    end

    def rewind
      @io.rewind
    end

    def size
      @io.size
    end

    def close
      @io.close
    end
  end

  class FakeDecodedImage
    def initialize(path)
      @path = path
    end

    def validate!
      raise MiniMagick::Invalid, 'truncated image' if File.size(@path) < 16
      true
    end

    def type
      head = File.binread(@path, 12)
      return 'PNG' if head.start_with?("\x89PNG\r\n\x1A\n".b)
      return 'JPEG' if head.start_with?("\xFF\xD8\xFF".b)
      return 'GIF' if head.start_with?('GIF89a', 'GIF87a')
      'UNKNOWN'
    end

    def dimensions
      [9, 9]
    end
  end

  def with_input(bytes, filename, declared_type)
    Dir.mktmpdir('cafe-precache-ci-') do |dir|
      AvatarUploader.root = dir
      AvatarUploader.enable_processing = false
      original = File.join(dir, 'incoming_binary')
      File.binwrite(original, bytes)
      input = UploadedFile.new(original, filename, declared_type)
      uploader = AvatarUploader.new
      begin
        MiniMagick::Image.stub(:new, ->(path) { FakeDecodedImage.new(path) }) do
          yield uploader, input, dir
        end
      ensure
        input.close
      end
    end
  end

  def cache_files(dir)
    Dir.glob(File.join(dir, 'uploads', '**', '*')).select { |item| File.file?(item) }
  end

  def test_truncated_jpeg_rejected_before_public_cache_is_written
    with_input("\xFF\xD8\xFF".b, 'broken.jpg', 'image/jpeg') do |uploader, input, dir|
      assert_raises(CarrierWave::IntegrityError) { uploader.cache!(input) }
      assert_empty cache_files(dir)
    end
  end

  def test_invalid_signatures_extensions_mime_and_sizes_never_written_to_public_cache
    valid_png = "\x89PNG\r\n\x1A\n".b + ('x'.b * 40)
    samples = [
      ['<script>alert(1)</script>'.b, 'attack.jpg', 'image/jpeg'],
      ['<svg xmlns="http://www.w3.org/2000/svg"/>'.b, 'vector.svg', 'image/svg+xml'],
      [valid_png, 'bad.jpg', 'image/jpeg'],
      [valid_png, 'good.png', 'text/plain'],
      [valid_png, 'bad.svg', 'image/png'],
      [''.b, 'empty.png', 'image/png'],
      ["\xFF\xD8\xFF".b + ('A'.b * 2097152), 'large.jpg', 'image/jpeg']
    ]
    samples.each do |bytes, filename, mime|
      with_input(bytes, filename, mime) do |uploader, input, dir|
        assert_raises(CarrierWave::IntegrityError, filename) { uploader.cache!(input) }
        assert_empty cache_files(dir), filename
      end
    end
  end

  def test_valid_png_mechanics_can_cache_after_preflight
    # The mock tests the order of operations. True image decoding is reserved
    # for the owner's private ImageMagick-powered sandbox HTTP test.
    valid_png = "\x89PNG\r\n\x1A\n".b + ('valid-sample'.b * 4)
    with_input(valid_png, 'valid.png', 'image/png') do |uploader, input, dir|
      uploader.cache!(input)
      assert uploader.cached?
      refute_empty cache_files(dir)
    end
  end

  def test_mime_and_pixel_limits_declared
    u = AvatarUploader.new
    assert_equal 1..(2 * 1024 * 1024), u.size_range
    assert_equal %w(jpg jpeg png gif), u.extension_allowlist
    assert_match u.content_type_allowlist.first, 'image/jpeg'
  end
end
