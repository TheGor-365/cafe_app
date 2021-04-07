# This file should contain all the record creation needed to seed the database with its default values.
# The data can then be loaded with the rails db:seed command (or created alongside the database with db:setup).
#
# Examples:
#
#   movies = Movie.create([{ name: 'Star Wars' }, { name: 'Lord of the Rings' }])
#   Character.create(name: 'Luke', movie: movies.first)

User.create([
  { username: 'sarah',    email: 'sarah@example.com',     password: 'Password', password_confirmation: 'password', admin: true },
  { username: 'emily',    email: 'emily@example.com',     password: 'Password' },
  { username: 'melanie',  email: 'melanie@example.com',   password: 'Password' },
  { username: 'caroline', email: 'caroline@example.com',  password: 'Password' },
  { username: 'bridget',  email: 'bridget@example.com',   password: 'Password' }
])

25.times do |i|
  Product.ceate!(
    name: 'Pizza',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua',
    price: 11.99,
    catering_item: true
  )
end
