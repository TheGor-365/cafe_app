class CreateCafeDrinkOptions < ActiveRecord::Migration[6.0]
  def change
    create_table :product_variants do |t|
      t.references :product, null: false, foreign_key: true
      t.string :code, null: false
      t.string :label, null: false
      t.integer :price_cents, null: false
      t.boolean :available, null: false, default: true
      t.timestamps
    end
    add_index :product_variants, [:product_id, :code], unique: true

    create_table :product_modifier_options do |t|
      t.references :product, null: false, foreign_key: true
      t.string :group_code, null: false
      t.string :code, null: false
      t.string :label, null: false
      t.integer :price_cents, null: false, default: 0
      t.boolean :available, null: false, default: true
      t.timestamps
    end
    add_index :product_modifier_options, [:product_id, :group_code, :code],
              unique: true, name: 'index_coffee_modifiers_on_product_group_code'

    add_reference :order_items, :product_variant, foreign_key: true, null: true
    add_column :order_items, :variant_label_snapshot, :string

    create_table :order_item_modifiers do |t|
      t.references :order_item, null: false, foreign_key: true
      t.references :product_modifier_option, null: false, foreign_key: true
      t.string :group_code_snapshot, null: false
      t.string :label_snapshot, null: false
      t.integer :price_cents_snapshot, null: false
      t.timestamps
    end
    add_index :order_item_modifiers, [:order_item_id, :group_code_snapshot],
              unique: true, name: 'index_coffee_cart_options_on_line_and_group'
  end
end
