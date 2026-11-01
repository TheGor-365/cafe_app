# Deterministic, idempotent catalog-only sample data for local development.
# Never create a login or administrator from checked-in credentials.
unless Rails.env.development? || Rails.env.test?
  raise 'Cafe demo seeds are intentionally disabled outside development/test'
end

[
  ['Pizza', "It's so good, daugh!"],
  ['Pasta', 'We cannoli do so much in each vide'],
  ['Desserts', 'Rock rails icecream']
].each do |heading, body|
  category = Category.find_or_initialize_by(heading: heading)
  category.body = body
  category.display = true
  category.save!
end

puts 'Cafe local sample categories are ready. No accounts were created.'
