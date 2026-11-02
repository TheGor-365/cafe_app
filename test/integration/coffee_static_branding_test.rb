require 'test_helper'

class CoffeeStaticBrandingTest < ActionDispatch::IntegrationTest
  test 'homepage has brand title, mobile viewport and a first party favicon' do
    get root_path
    assert_response :success
    assert_select 'html[lang=en]', count: 1
    assert_select 'title', text: /Gor.s Coffee/
    assert_select 'meta[name=viewport][content=?]', 'width=device-width, initial-scale=1', count: 1
    assert_select 'meta[name=description]', count: 1
    assert_select 'link[rel=icon][type="image/svg+xml"][href="/favicon.svg"]', count: 1
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
    refute_includes svg, 'http://', 'No remote asset references except XML namespace'
    refute_includes svg, 'https://'
  end

  test 'README accurately documents draft-only status and legacy limitations' do
    readme = Rails.root.join('README.md').read
    assert_includes readme, 'Gor\'s Coffee'
    assert_includes readme, 'Русский'
    assert_includes readme, 'English'
    assert_includes readme, 'Ruby 2.5.8'
    assert_includes readme, 'Draft PR'
    assert_includes readme, 'No real checkout'
    assert_includes readme, '/products/:id'
  end
end
