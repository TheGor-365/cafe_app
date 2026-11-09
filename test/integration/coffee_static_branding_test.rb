require 'test_helper'

class CoffeeStaticBrandingTest < ActionDispatch::IntegrationTest
  test 'homepage has brand title, mobile viewport and a first party favicon' do
    get root_path
    assert_response :success
    assert_select 'html[lang=en]', count: 1
    assert_select 'title', text: /Gor.s Coffee/
    assert_select 'meta[name=viewport][content=?]', 'width=device-width, initial-scale=1', count: 1
    assert_select 'meta[name=description]', count: 1
    assert_select 'link[rel=icon][type="image/svg+xml"][href="/favicon.svg?v=20261109"]', count: 1
    assert_select 'meta[name=theme-color][content="#2c1c14"]', count: 1
  end

  test '404 422 and 500 are self contained styled readable demo pages' do
    %w[404 422 500].each do |status|
      html = Rails.root.join('public', "#{status}.html").read
      doc = Nokogiri::HTML(html)

      assert_equal 'en', doc.at_css('html')['lang']
      assert doc.at_css('meta[name=viewport]'), "Missing viewport for #{status}"
      assert doc.at_css('link[rel=icon][href="/favicon.svg"]'), "Missing icon for #{status}"
      assert doc.at_css('main h1'), "Missing heading for #{status}"
      assert doc.at_css('style'), "Static error #{status} must not rely on Rails assets"
      assert doc.at_css('a[href="/"]'), "Missing homepage return link for #{status}"
      assert doc.at_css('a[href="/menu"]'), "Missing menu fallback link for #{status}"
      assert_includes doc.text, 'portfolio demonstration'
      refute_includes html, 'assets/application', "Error #{status} must not require compiled assets"
      refute_includes html, 'check the logs', "Error #{status} must not expose internal hints"
    end
  end

  test 'new SVG favicon exists without remote dependencies' do
    svg = Rails.root.join('public', 'favicon.svg').read
    doc = Nokogiri::XML(svg)
    assert_empty doc.errors
    assert_equal 'svg', doc.root.name
    assert_equal 'http://www.w3.org/2000/svg', doc.root.namespace.href
    assert_includes svg, 'viewBox="0 0 64 64"'
    assert_empty doc.xpath('//*[local-name()="script" or local-name()="image"]')
    refute_includes svg, 'href="http', 'SVG must not link external files'
  end

  test 'README accurately documents the educational preview and intermediate legacy stack' do
    readme = Rails.root.join('README.md').read
    assert_includes readme, "Gor's Coffee"
    assert_includes readme, 'Русский'
    assert_includes readme, 'English'
    assert_includes readme, 'Ruby 2.7.8'
    assert_includes readme, 'Rails 6.1.7.10'
    assert_includes readme, 'fictional checkout'
    assert_includes readme, 'No payments'
    assert_includes readme, 'CAFE_PREVIEW_SEED_ALLOWED'
    assert_includes readme, 'not a real café'
  end
end
