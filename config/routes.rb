Rails.application.routes.draw do

  get 'cart/show'
  resources :categories
  resources :products

  devise_for :users

  root to: 'pages#home'

  get 'menu', to: 'menu#index'
  get 'catering', to: 'pages#catering'
  get 'info', to: 'pages#info'
  get 'search', to: 'menu#search'

end
