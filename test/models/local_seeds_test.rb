require 'test_helper'

class LocalSeedsTest < ActiveSupport::TestCase
  test 'sample seeds are repeatable and never provision an admin' do
    before_admin = User.where(admin: true).count

    2.times { load Rails.root.join('db/seeds.rb').to_s }

    %w[Pizza Pasta Desserts].each do |heading|
      assert_equal 1, Category.where(heading: heading).count
    end
    assert_equal before_admin, User.where(admin: true).count
  end
end
