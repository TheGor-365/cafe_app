# Local-only, repeatable, fictional coffee-shop catalog. Never provision user
# accounts or execute this task outside development/test environments.
unless Rails.env.development? || Rails.env.test?
  raise 'Cafe demo seeds are intentionally disabled outside development/test'
end

# Preserve the legacy academic categories; never delete existing products.
category_descriptions = {
  'Coffee' => 'Espresso classics and comforting café favourites',
  'Tea & Matcha' => 'Tea, ceremonial-inspired matcha and warm spice',
  'Iced Drinks' => 'Cold brew and chilled café drinks',
  'Bakery' => 'Pastries fresh from the demo bakery',
  'Breakfast' => 'Light plates for an easy morning',
  'Desserts' => 'Something sweet with your favourite drink',
  'Pizza' => "It's so good, daugh!",
  'Pasta' => 'We cannoli do so much in each vide'
}

category_descriptions.each do |heading, body|
  category = Category.find_or_initialize_by(heading: heading)
  category.body = body
  category.display = true
  category.save!
end

demo_items = [
  ['Coffee', 'Espresso', 'A rich, short shot with deep roasted notes.', 2.50, true, true],
  ['Coffee', 'Double Espresso', 'Double the espresso for a bold start.', 3.25, true, true],
  ['Coffee', 'Americano', 'Espresso softened with hot water.', 3.10, true, true],
  ['Coffee', 'Cappuccino', 'Espresso, steamed milk and silky foam.', 4.25, false, false],
  ['Coffee', 'Flat White', 'Double espresso with velvety steamed milk.', 4.50, false, false],
  ['Coffee', 'Caffè Latte', 'Smooth espresso with generous steamed milk.', 4.75, false, false],
  ['Coffee', 'Mocha', 'Espresso with chocolate and steamed milk.', 5.10, false, false],
  ['Tea & Matcha', 'Matcha Latte', 'Green tea with a gentle milk finish.', 5.25, false, false],
  ['Tea & Matcha', 'Masala Chai', 'Black tea brewed with warming spices and milk.', 4.50, false, false],
  ['Tea & Matcha', 'Earl Grey Tea', 'Black tea with bright bergamot aroma.', 3.00, true, true],
  ['Iced Drinks', 'Iced Americano', 'Espresso over cold water and ice.', 3.75, true, true],
  ['Iced Drinks', 'Cold Brew', 'Slow-steeped coffee served chilled.', 4.60, true, true],
  ['Iced Drinks', 'Iced Latte', 'Espresso, cold milk and ice.', 4.95, false, false],
  ['Bakery', 'Butter Croissant', 'Flaky golden pastry, baked until crisp.', 3.70, false, false],
  ['Bakery', 'Almond Croissant', 'Croissant finished with almond filling.', 4.45, false, false],
  ['Bakery', 'Cinnamon Roll', 'Soft rolled pastry with cinnamon icing.', 4.10, false, false],
  ['Breakfast', 'Avocado Toast', 'Toast topped with avocado and herbs.', 8.50, true, true],
  ['Breakfast', 'Granola Bowl', 'Granola, yoghurt and seasonal fruit.', 7.80, false, false],
  ['Desserts', 'Classic Cheesecake', 'Creamy cheesecake with a biscuit crust.', 6.10, false, false],
  ['Desserts', 'Dark Chocolate Brownie', 'Soft-centred brownie for chocolate lovers.', 4.80, false, false]
]

demo_items.each_with_index do |(category_name, name, description, price, vegan, dairy_free), index|
  category = Category.find_by!(heading: category_name)
  product = Product.find_or_initialize_by(name: name, category: category)
  product.assign_attributes(
    description: description,
    price: price,
    available: true,
    featured: index < 7 || %w[Cold\ Brew Matcha\ Latte].include?(name),
    vegan: vegan,
    dairy_free: dairy_free,
    vegetarian: true
  )
  product.save!
end

puts "Demo café catalog ready: #{demo_items.size} curated products; no accounts created."
