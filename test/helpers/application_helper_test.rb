require 'test_helper'

class ApplicationHelperTest < ActionView::TestCase
  test "renders notices without executable JavaScript" do
    html = toastr_flash(notice: "Saved successfully")
    assert_includes html, "Saved successfully"
    assert_includes html, 'class="alert alert-success"'
    assert_not_includes html, "<script"
  end

  test "escapes hostile flash messages even if marked html_safe" do
    message = %q{</script><img src=x onerror="alert('xss')">}.html_safe
    html = toastr_flash(alert: message)

    assert_includes html, "&lt;/script&gt;"
    assert_includes html, "&lt;img"
    assert_not_includes html, "</script>"
    assert_not_includes html, "<img"
    assert_includes html, 'class="alert alert-danger"'
  end

  test "uses a fixed CSS class for unknown flash keys" do
    html = toastr_flash("evil<script>" => "Unknown")
    assert_includes html, 'class="alert alert-info"'
    assert_not_includes html, "evil<script>"
  end

  test "ignores blank notifications" do
    assert_equal "", toastr_flash(notice: nil, alert: "")
  end
end
