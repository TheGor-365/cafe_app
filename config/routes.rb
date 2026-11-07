Rails.application.routes.draw do

  devise_for :users
  get 'account', to: 'account#show', as: :account

  root to: 'pages#home'

  resources :categories
  resources :products
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
