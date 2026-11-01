# Coffee storefront — homepage and HTML cart, 2026-11-02

## Scope
- Compact Gor's Coffee brand partial replacing 10em text; retains user's local outer application layout and avatar.
- Working Home/ Menu/ Cart/ Catering/ Info links with no dead customer reviews link.
- Featured sample products and category CTA on responsive homepage, clearly labeled as fictional demo business.
- HTML fallback: menu Add to cart -> /cart -> quantity update or remove -> cart state. Kept pre-existing AJAX endpoints and tested them, but HTML flow is the preferred reliable baseline.
- All products priced server-side; reject unavailable product; do not accept client-supplied price or replacement product.
- Session-scoped cart; no checkout or real payment yet.
- Explicitly no changes to `Gemfile`, `Gemfile.lock`, `db/schema.rb`, historical migrations, avatar uploader, photos or `app/views/layouts/application.html.erb`.
- Dependencies tested in CI: Ruby 2.5.8, Rails 6.0.3.6 remote baseline; local Rails 6.0.6.1 HTTP browser smoke still needed.

## Local delivery (no merge until dirty tree reconciled)
Import only:
`app/controllers/pages_controller.rb`, `app/controllers/cart_controller.rb`, `app/controllers/order_items_controller.rb`, `app/views/pages/home.html.erb`, `app/views/cart/show.html.erb`, `app/views/cart/_cart_items.html.erb`, `app/views/layouts/_title.html.erb`, `app/views/layouts/_links.html.erb`, `app/views/menu/_products.html.erb`, `app/assets/stylesheets/cafe_home_cart.scss`, `test/integration/coffee_home_cart_flow_test.rb`.

Check diffs before import; user's local staged/unstaged files and private uploads must be preserved. This new partial brand is distinct from the modified application layout and does not affect avatar render. Do not push backup media, change credentials, merge to master or deploy.
