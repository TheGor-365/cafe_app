require 'test_helper'

class CoffeeDrinkSeedTest < ActiveSupport::TestCase
  test 'sample drinks get three repeatable sizes and modifiers without accounts' do
    before = User.count
    2.times { load Rails.root.join('db/seeds.rb').to_s }

    drink = Product.find_by!(name: 'Cappuccino')
    assert_equal 3, drink.product_variants.count
    assert_equal 5, drink.product_modifier_options.count
    assert_equal [425, 500, 575], drink.product_variants.order(:price_cents).pluck(:price_cents)
    assert_equal before, User.count
    assert_equal 20, Product.where(name: [
      'Espresso', 'Double Espresso', 'Americano', 'Cappuccino',
      'Flat White', 'Caffè Latte', 'Mocha', 'Matcha Latte',
      'Masala Chai', 'Earl Grey Tea', 'Iced Americano', 'Cold Brew',
      'Iced Latte', 'Butter Croissant', 'Almond Croissant',
      'Cinnamon Roll', 'Avocado Toast', 'Granola Bowl',
      'Classic Cheesecake', 'Dark Chocolate Brownie'
    ]).count
  end
end
