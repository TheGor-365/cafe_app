ActiveRecord::Schema.define(version: 2026_11_07_000200) do

  enable_extension "plpgsql"

  create_table "categories", force: :cascade do |t|
    t.string "heading"
    t.text "body"
    t.boolean "display"
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
  end

  create_table "order_items", force: :cascade do |t|
    t.integer "quantity"
    t.bigint "product_id", null: false
    t.bigint "product_variant_id"
    t.string "variant_label_snapshot"
    t.bigint "order_id", null: false
    t.decimal "total"
    t.decimal "unit_price"
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.index ["order_id"], name: "index_order_items_on_order_id"
    t.index ["product_id"], name: "index_order_items_on_product_id"
    t.index ["product_variant_id"], name: "index_order_items_on_product_variant_id"
  end

  create_table "product_variants", force: :cascade do |t|
    t.bigint "product_id", null: false
    t.string "code", null: false
    t.string "label", null: false
    t.integer "price_cents", null: false
    t.boolean "available", default: true, null: false
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.index ["product_id", "code"], name: "index_product_variants_on_product_id_and_code", unique: true
    t.index ["product_id"], name: "index_product_variants_on_product_id"
  end

  create_table "product_modifier_options", force: :cascade do |t|
    t.bigint "product_id", null: false
    t.string "group_code", null: false
    t.string "code", null: false
    t.string "label", null: false
    t.integer "price_cents", default: 0, null: false
    t.boolean "available", default: true, null: false
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.index ["product_id", "group_code", "code"], name: "index_coffee_modifiers_on_product_group_code", unique: true
    t.index ["product_id"], name: "index_product_modifier_options_on_product_id"
  end

  create_table "order_item_modifiers", force: :cascade do |t|
    t.bigint "order_item_id", null: false
    t.bigint "product_modifier_option_id", null: false
    t.string "group_code_snapshot", null: false
    t.string "label_snapshot", null: false
    t.integer "price_cents_snapshot", null: false
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.index ["order_item_id", "group_code_snapshot"], name: "index_coffee_cart_options_on_line_and_group", unique: true
    t.index ["order_item_id"], name: "index_order_item_modifiers_on_order_item_id"
    t.index ["product_modifier_option_id"], name: "index_order_item_modifiers_on_product_modifier_option_id"
  end

  create_table "orders", force: :cascade do |t|
    t.string "status", default: "cart", null: false
    t.string "pickup_name"
    t.string "pickup_slot"
    t.text "pickup_note"
    t.datetime "placed_at", precision: 6
    t.bigint "user_id"
    t.decimal "subtotal"
    t.decimal "total"
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.index ["status", "placed_at"], name: "index_orders_on_status_and_placed_at"
    t.index ["user_id"], name: "index_orders_on_user_id"
  end

  create_table "products", force: :cascade do |t|
    t.string "name", default: ""
    t.text "description", default: ""
    t.decimal "price", default: "0.0"
    t.boolean "dairy_free", default: false
    t.boolean "gluten_free", default: false
    t.boolean "kosher", default: false
    t.boolean "peanut_free", default: false
    t.boolean "vegan", default: false
    t.boolean "vegetarian", default: false
    t.boolean "available", default: true
    t.boolean "catering", default: false
    t.boolean "featured", default: false
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.bigint "category_id"
    t.string "image"
    t.index ["category_id"], name: "index_products_on_category_id"
  end

  create_table "users", force: :cascade do |t|
    t.string "username", default: "", null: false
    t.string "email", default: "", null: false
    t.string "encrypted_password", default: "", null: false
    t.string "reset_password_token"
    t.datetime "reset_password_sent_at"
    t.datetime "remember_created_at"
    t.integer "sign_in_count", default: 0, null: false
    t.datetime "current_sign_in_at"
    t.datetime "last_sign_in_at"
    t.inet "current_sign_in_ip"
    t.inet "last_sign_in_ip"
    t.string "confirmation_token"
    t.datetime "confirmed_at"
    t.datetime "confirmation_sent_at"
    t.string "unconfirmed_email"
    t.datetime "created_at", precision: 6, null: false
    t.datetime "updated_at", precision: 6, null: false
    t.boolean "admin", default: false
    t.index ["email"], name: "index_users_on_email", unique: true
    t.index ["reset_password_token"], name: "index_users_on_reset_password_token", unique: true
    t.index ["username"], name: "index_users_on_username", unique: true
  end

  add_foreign_key "order_items", "orders"
  add_foreign_key "order_items", "products"
  add_foreign_key "order_items", "product_variants"
  add_foreign_key "order_item_modifiers", "order_items"
  add_foreign_key "order_item_modifiers", "product_modifier_options"
  add_foreign_key "product_modifier_options", "products"
  add_foreign_key "product_variants", "products"
  add_foreign_key "products", "categories"
  add_foreign_key "orders", "users"
end
