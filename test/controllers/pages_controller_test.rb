require 'test_helper'

class PagesControllerTest < ActionDispatch::IntegrationTest
  test 'public home page responds through the current root route' do
    get root_path
    assert_response :success
    assert_select 'h1#cafe-home-heading', count: 1
  end

  test 'public catering information uses the current route' do
    get catering_path
    assert_response :success
  end

  test 'public project information uses the current route' do
    get info_path
    assert_response :success
  end
end
