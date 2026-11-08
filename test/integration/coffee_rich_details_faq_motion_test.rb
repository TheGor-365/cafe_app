require 'test_helper'

class CoffeeRichDetailsAndFaqMotionTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Rich Detail QA Coffee', display: true)
    @drink = Product.create!(name: 'QA Rich Latte', category: @category,
                             description: 'Sample coffee served as a demo item.',
                             price: 4.50, available: true, vegan: true)
    @size = ProductVariant.create!(product: @drink, code: 'M', label: 'Medium - 350 ml',
                                   price_cents: 525, available: true)
    ProductVariant.create!(product: @drink, code: 'L', label: 'Large - 470 ml',
                           price_cents: 625, available: false)
    @extra = ProductModifierOption.create!(product: @drink,
                                           group_code: 'syrup', code: 'vanilla',
                                           label: 'Vanilla', price_cents: 55,
                                           available: true)
    ProductModifierOption.create!(product: @drink,
                                  group_code: 'shot', code: 'espresso',
                                  label: 'Extra espresso', price_cents: 90,
                                  available: false)
    @related = Product.create!(name: 'QA Related Americano', category: @category,
                               description: 'Another sample coffee', price: 3.25, available: true)
    @hidden = Product.create!(name: 'QA Hidden Coffee', category: @category,
                              description: 'Unavailable sample', price: 4.25, available: false)
    @other_category = Category.create!(heading: 'Rich Detail QA Bakery', display: true)
    Product.create!(name: 'QA Other Bakery Product', category: @other_category,
                    description: 'A separate category', price: 4.20, available: true)
  end

  test 'details provide real options, price breakdown and only positive demo labels' do
    get product_path(@drink)
    assert_response :success
    assert_select 'section.coffee-product-detail__information' do
      assert_select 'h2#coffee-detail-facts-title', text: /closer look/
      assert_select 'dl.coffee-product-detail__facts dt', text: 'Menu category'
      assert_select 'dd', text: @category.heading, count: 1
      assert_select 'dd', text: '$5.25', minimum: 1
      assert_select '.coffee-product-detail__price-list li', text: /Medium - 350 ml/, count: 1
      assert_select '.coffee-product-detail__price-list li', text: /Large - 470 ml/, count: 0
      assert_select '.coffee-product-detail__price-list li', text: /Vanilla/, count: 1
      assert_select '.coffee-product-detail__price-list li', text: /Extra espresso/, count: 0
      assert_select '.coffee-product-detail__dietary-list li', text: 'Vegan', count: 1
      assert_select '.coffee-product-detail__dietary-list li', text: 'Dairy free', count: 0
      assert_select '.coffee-product-detail__caution', text: /not been independently verified/
    end
    assert_select 'form[action=?]', order_items_path, count: 1
  end

  test 'details suggest relevant available products without inventing recommendations' do
    get product_path(@drink)
    assert_response :success
    assert_select 'section.coffee-product-detail__related' do
      assert_select "a[href='#{product_path(@related)}']", count: 1
      assert_select "a[href='#{product_path(@drink)}']", count: 0
      assert_select "a[href='#{product_path(@hidden)}']", count: 0
      assert_select 'a[href*="other-bakery"]', count: 0
      assert_select 'article.coffee-product-detail__related-card', count: 1
    end
  end

  test 'non-configurable product describes single price and no optional extras' do
    get product_path(@related)
    assert_response :success
    assert_select 'section.coffee-product-detail__information' do
      assert_select '.coffee-product-detail__info-card', text: /one standard price/
      assert_select '.coffee-product-detail__info-card', text: /No additional customizations/
      assert_select '.coffee-product-detail__info-card', text: /No dietary suitability attributes/
    end
    assert_select 'form[action=?]', order_items_path, count: 1
  end

  test 'FAQ remains semantic and animation respects reduced motion' do
    get info_path
    assert_response :success
    assert_select 'section#faq .cafe-content-page__faq details', count: 5 do
      assert_select 'summary', count: 5
    end
    scss = Rails.root.join('app/assets/stylesheets/cafe_public_pages.scss').read
    compiled = SassC::Engine.new(scss, syntax: :scss).render
    assert_includes compiled, '.cafe-content-page__faq details::details-content'
    assert_includes compiled, '.cafe-content-page__faq details[open]::details-content'
    assert_includes compiled, 'transition: block-size'
    assert_includes compiled, '@media (prefers-reduced-motion: reduce)'
    assert_includes compiled, 'transition: none'
  end
end
