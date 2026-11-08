# frozen_string_literal: true

# Candidate for an isolated QA-only bind mount to
# /app/app/uploaders/avatar_uploader.rb. This file deliberately lives outside
# the real app tree in GitHub: the owner's local AvatarUploader is not tracked
# upstream and must not be overwritten or silently replaced.
#
# Requires patched CarrierWave >= 2.2.7 and < 3, currently verified for the
# Ruby 2.5 / Rails 6 stack only in disposable CI, NOT in the local runtime.
#
# This is a defense-in-depth policy, not approval to expose public uploads.
# MIME allowlist, magic bytes, filename extension, and strict byte-size cap
# must all agree. Keep ImageMagick policy limits / response nosniff as
# independent release checks.

require 'carrierwave'

class AvatarUploader < CarrierWave::Uploader::Base
  include CarrierWave::MiniMagick
  storage :file

  MAX_UPLOAD_BYTES = 2 * 1024 * 1024

  # Preserve the live application's CarrierWave store path.
  def store_dir
    "uploads/#{model.class.to_s.underscore}/#{mounted_as}/#{model.id}"
  end

  def extension_allowlist
    %w(jpg jpeg png gif)
  end

  def content_type_allowlist
    [/\Aimage\/(?:jpeg|png|gif)\z/]
  end

  def size_range
    1..MAX_UPLOAD_BYTES
  end

  # Explicit server-side validation catches spoofed extensions and invalid
  # length even when the browser provides an arbitrary Content-Type header.
  # CarrierWave's own content_type_allowlist and size_range run as well.
  process :verify_image_bytes!

  version :thumb do
    process resize_to_fit: [50, 50]
  end

  def verify_image_bytes!
    candidate = file
    raise CarrierWave::IntegrityError, 'No image provided' unless candidate

    path = candidate.path
    raise CarrierWave::IntegrityError, 'Image has no readable data' unless path && ::File.file?(path)

    length = ::File.size(path)
    unless length >= 1 && length <= MAX_UPLOAD_BYTES
      raise CarrierWave::IntegrityError, 'Image must be at most 2 MB'
    end

    head = ::File.open(path, 'rb') { |handle| handle.read(12) } || ''
    detected = if head.start_with?("\x89PNG\r\n\x1A\n".b)
                 :png
               elsif head.start_with?("\xFF\xD8\xFF".b)
                 :jpeg
               elsif head.start_with?('GIF87a', 'GIF89a')
                 :gif
               end

    ext = ::File.extname(candidate.original_filename.to_s).downcase
    extensions = { png: %w(.png), jpeg: %w(.jpg .jpeg), gif: %w(.gif) }

    unless detected && extensions.fetch(detected).include?(ext)
      raise CarrierWave::IntegrityError, 'Image bytes and filename do not match'
    end
  end
end
