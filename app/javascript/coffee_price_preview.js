/*
 * Progressive price preview for the demo coffee configurator.
 * Display-only: Rails validates every variant, add-on and final price on POST.
 * Integer cents avoid floating-point drift. Works with Turbolinks and plain HTML.
 */
'use strict'

const MAX_QUANTITY = 20

function validCents(value) {
  return Number.isSafeInteger(value) && value >= 0
}

function computePriceCents(basePriceCents, extraPriceCents, quantity) {
  if (!validCents(basePriceCents) ||
      !Array.isArray(extraPriceCents) ||
      !Number.isSafeInteger(quantity) ||
      quantity < 1 || quantity > MAX_QUANTITY ||
      !extraPriceCents.every(validCents)) {
    return null
  }

  const unitCents = extraPriceCents.reduce((sum, price) => sum + price, basePriceCents)
  const totalCents = unitCents * quantity

  if (!Number.isSafeInteger(unitCents) || !Number.isSafeInteger(totalCents)) return null

  return { unitCents, totalCents }
}

function integerFromAttribute(value) {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) ? parsed : null
}

function formatCents(cents) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}

function updateCoffeePrice(form) {
  const output = form.querySelector('[data-coffee-price-output]')
  if (!output) return

  const variant = form.querySelector('select[name="order_item[product_variant_id]"]')
  const quantityField = form.querySelector('[data-coffee-quantity]')
  const unitLabel = form.querySelector('[data-coffee-unit-price]')
  const totalLabel = form.querySelector('[data-coffee-total-price]')
  const button = form.querySelector('input[type="submit"], button[type="submit"]')
  if (!quantityField || !unitLabel || !totalLabel) return

  const basePriceCents = variant
    ? integerFromAttribute(variant.selectedOptions[0] && variant.selectedOptions[0].getAttribute('data-price-cents'))
    : integerFromAttribute(form.getAttribute('data-base-price-cents'))
  const addOnPrices = Array.from(form.querySelectorAll('select[name="order_item[modifier_option_ids][]"]'))
    .map(select => integerFromAttribute(select.selectedOptions[0] && select.selectedOptions[0].getAttribute('data-price-cents')))
  const quantity = Number(quantityField.value)
  const result = computePriceCents(basePriceCents, addOnPrices, quantity)

  if (result) {
    unitLabel.textContent = 'Unit: ' + formatCents(result.unitCents)
    totalLabel.textContent = 'Total: ' + formatCents(result.totalCents)
    output.setAttribute('data-price-valid', 'true')
    if (button) button.disabled = false
  } else {
    unitLabel.textContent = 'Check your selection'
    totalLabel.textContent = 'Total unavailable'
    output.setAttribute('data-price-valid', 'false')
    if (button) button.disabled = true
  }
}

function initializeCoffeePricePreviews() {
  if (typeof document === 'undefined') return

  document.querySelectorAll('form[data-coffee-price-form]').forEach(form => {
    if (form.getAttribute('data-coffee-price-initialized') === 'true') return
    form.setAttribute('data-coffee-price-initialized', 'true')
    form.addEventListener('input', () => updateCoffeePrice(form))
    form.addEventListener('change', () => updateCoffeePrice(form))
    updateCoffeePrice(form)
  })
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', initializeCoffeePricePreviews)
  document.addEventListener('turbolinks:load', initializeCoffeePricePreviews)
  if (document.readyState !== 'loading') initializeCoffeePricePreviews()
}

module.exports = { computePriceCents, integerFromAttribute, formatCents, updateCoffeePrice, initializeCoffeePricePreviews }
