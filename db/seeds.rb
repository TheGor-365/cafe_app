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

Category.create!(heading: 'Pizza', body: "It's so good, daugh!", display: true)
Category.create!(heading: 'Pasta', body: "We cannoli do so much in each vide", display: true)
Category.create!(heading: 'Desserts', body: "Rock rails icecream", display: true)

# 10.times do |i|
#   pizza = Product.new(
#     name: 'Pizza',
#     description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua',
#     price: 11.99,
#     catering: true,
#     category: Category.find(1)
#   )
#
#   pasta = Product.new(
#     name: 'Pasta',
#     description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua',
#     price: 8.99,
#     catering: true,
#     category: Category.find(2)
#   )
#
#   dessert = Product.new(
#     name: 'Icecream',
#     description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua',
#     price: 6.99,
#     catering: true,
#     category: Category.find(3)
#   )
#
#   pizza.image.url("#{i}_pizza_image.jpg")
#   pasta.image.url("#{i}_pasta_image.jpg")
#   dessert.image.url("#{i}_dessert_image.jpg")

#   if i == 5
#     pizza.featured = true
#     pasta.featured = true
#     dessert.featured = true
#   end
#
#   pizza.save
#   pasta.save
#   dessert.save
# end
