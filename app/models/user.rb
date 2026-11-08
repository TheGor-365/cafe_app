class User < ApplicationRecord
  # Include default devise modules. Others available are:
  # :confirmable, :lockable, :timeoutable, :trackable and :omniauthable
  has_many :demo_orders, class_name: 'Order', dependent: :nullify

  # The database has a UNIQUE index on username; reject blank/duplicate values
  # before they reach PostgreSQL rather than raising a 500 during sign-up.
  validates :username, presence: true, length: { minimum: 3, maximum: 40 },
                       uniqueness: { case_sensitive: false },
                       format: { with: /\A[a-zA-Z0-9_]+\z/,
                                 message: 'can contain only letters, numbers and underscores' }


  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable
end
