module ProductsHelper

  def product_image product
    image_path = product.image.present? ? product.image.url : 'product.jpg'
    image_tag(image_path, class: 'img-fluid')
  end

end
