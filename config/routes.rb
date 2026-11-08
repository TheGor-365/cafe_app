Rails.application.routes.draw do

  devise_for :users
  get 'account', to: 'account#show', as: :account
  get 'owner/access', to: 'owner_access#new', as: :new_owner_access
  post 'owner/access', to: 'owner_access#create', as: :owner_access

  root to: 'pages#home'

  resources :categories
  resources :products do
    resources :product_variants, except: %i[show]
    resources :product_modifier_options, except: %i[show]
  end
  resources :order_items

  get 'menu',     to: 'menu#index'
  get 'search',   to: 'menu#search'
  get 'cart',     to: 'cart#show'
  get 'demo_checkout', to: 'demo_orders#new', as: :demo_checkout
  resources :demo_orders, only: %i[create show]
  get 'admin/demo_orders', to: 'demo_orders#index', as: :admin_demo_orders
  patch 'admin/demo_orders/:id/status', to: 'demo_orders#update', as: :admin_demo_order_status
  post 'cart/consolidate', to: 'cart#consolidate', as: :consolidate_cart
  
  get 'info',     to: 'pages#info'
  get 'catering', to: 'pages#catering'

end
