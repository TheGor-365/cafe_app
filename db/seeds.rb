User.create([
  { username: 'sarah',    email: 'sarah@example.com',    password: 'Password', password_confirmation: 'password', admin: true },
  { username: 'emily',    email: 'emily@example.com',    password: 'Password' },
  { username: 'melanie',  email: 'melanie@example.com',  password: 'Password' },
  { username: 'caroline', email: 'caroline@example.com', password: 'Password' },
  { username: 'bridget',  email: 'bridget@example.com',  password: 'Password' }
])

Category.create!(heading: 'Pizza', body: "It's so good, daugh!", display: true)
Category.create!(heading: 'Pasta', body: "We cannoli do so much in each vide", display: true)
Category.create!(heading: 'Desserts', body: "Rock rails icecream", display: true)
