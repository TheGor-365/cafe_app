require 'test_helper'

class CoffeeAccountCornerStyleTest < ActionDispatch::IntegrationTest
  test 'account corner SCSS compiles and styles the real legacy sign-out button' do
    source = Rails.root.join('app/assets/stylesheets/zzzz_cafe_account_corner.scss').read
    css = SassC::Engine.new(source, syntax: :scss).render

    assert_includes css, '.page-container.row > .col-1.p-2 form button'
    assert_includes css, '.page-container.row > .col-1.p-2 form input[type="submit"]'
    assert_includes css, 'form input[type="submit"]:hover'
    assert_includes css, 'form input[type="submit"]:active'
    assert_includes css, 'form input[type="submit"]:focus-visible'
    assert_includes css, 'background: #714426'
    assert_includes css, ':focus-visible'
    assert_includes css, 'border-radius: 50% !important'
    assert_includes css, 'object-fit: cover'
  end

  test 'mobile breakpoints preserve space for both account and avatar columns' do
    source = Rails.root.join('app/assets/stylesheets/zzzz_cafe_account_corner.scss').read
    css = SassC::Engine.new(source, syntax: :scss).render

    assert_includes css, '@media (max-width: 760px)'
    assert_includes css, '@media (max-width: 360px)'
    assert_includes css, 'grid-template-areas: "nav nav" "avatar account" "main main"'
    assert_includes css, 'min-height: 44px'
    assert_includes css, 'overflow-wrap: anywhere'
    assert_includes css, '@media (prefers-reduced-motion: reduce)'
  end
end
