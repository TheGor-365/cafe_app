class AddDemoCheckoutToOrders < ActiveRecord::Migration[6.0]
  def change
    # Apply only to a verified isolated release environment; never replay
    # against the protected fifth synthetic PG or historical QA databases.
    add_column :orders, :status, :string, null: false, default: 'cart'
    add_column :orders, :pickup_name, :string
    add_column :orders, :pickup_slot, :string
    add_column :orders, :pickup_note, :text
    add_column :orders, :placed_at, :datetime
    add_reference :orders, :user, foreign_key: true, index: true
    add_index :orders, [:status, :placed_at]
  end
end
