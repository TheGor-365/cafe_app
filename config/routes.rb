Rails.application.routes.draw do

  resources :products

  devise_for :users

  root to: 'pages#home'

  get 'catering', to: 'pages#catering'
  get 'info', to: 'pages#info'

end
