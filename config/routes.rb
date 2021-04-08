Rails.application.routes.draw do

  devise_for :users

  root to: 'pages#home'

  resources :categories
  resources :products
  resources :order_items

  get 'menu',     to: 'menu#index'
  get 'catering', to: 'pages#catering'
  get 'info',     to: 'pages#info'
  get 'search',   to: 'menu#search'
  get 'cart',     to: 'cart#show'

end
