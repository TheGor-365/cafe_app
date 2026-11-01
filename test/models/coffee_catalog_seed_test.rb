require 'test_helper'

class CoffeeCatalogSeedTest < ActiveSupport::TestCase
  test 'coffee demo seeds create repeatable curated menu without accounts' do
    starting_users = User.count
    2.times { load Rails.root.join('db/seeds.rb').to_s }

    assert_equal starting_users, User.count
    %w[Coffee Bakery Breakfast].each do |heading|
      assert_equal 1, Category.where(heading: heading).count
    end
    assert_equal 1, Category.where(heading: 'Tea & Matcha').count
    assert_equal 1, Category.where(heading: 'Iced Drinks').count
    assert_equal 1, Product.where(name: 'Cappuccino').count
    assert_equal 1, Product.where(name: 'Cold Brew').count
    assert_equal 1, Product.where(name: 'Butter Croissant').count
    assert_operator Product.where(available: true).count, :>=, 20
  end
end
