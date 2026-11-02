/*
 * Accessible quantity +/- controls for menu configurators and cart lines.
 * The server-provided number field stays usable without JavaScript.
 * No automatic requests: cart still requires explicit Update.
 */
'use strict'

const MIN_QUANTITY = 1
const MAX_QUANTITY = 20
let installed = false

function parseQuantity(value) {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  const number = Number(value)
  return Number.isSafeInteger(number) ? number : null
}

function nextQuantity(value, step, min = MIN_QUANTITY, max = MAX_QUANTITY) {
  if ((step !== 1 && step !== -1) || !Number.isSafeInteger(min) ||
      !Number.isSafeInteger(max) || min < MIN_QUANTITY || max > MAX_QUANTITY || min > max) return null
  const current = parseQuantity(value)
  // An empty or invalid field is recovered to the minimum on either button.
  if (current === null) return min
  return Math.max(min, Math.min(max, current + step))
}

function fieldBounds(field) {
  const min = parseQuantity(field.getAttribute('min'))
  const max = parseQuantity(field.getAttribute('max'))
  return {
    min: min !== null && min >= MIN_QUANTITY && min <= MAX_QUANTITY ? min : MIN_QUANTITY,
    max: max !== null && max >= MIN_QUANTITY && max <= MAX_QUANTITY ? max : MAX_QUANTITY
  }
}

function refreshQuantityControl(control) {
  const field = control.querySelector('[data-coffee-quantity-input]')
  if (!field) return
  const { min, max } = fieldBounds(field)
  const current = parseQuantity(field.value)
  control.querySelectorAll('[data-coffee-quantity-step]').forEach(button => {
    const step = Number(button.getAttribute('data-coffee-quantity-step'))
    button.disabled = (step === -1 && current !== null && current <= min) ||
      (step === 1 && current !== null && current >= max)
  })
}

function initializeCoffeeQuantitySteppers() {
  if (typeof document === 'undefined') return
  document.querySelectorAll('[data-coffee-quantity-control]').forEach(control => {
    if (!control.querySelector('[data-coffee-quantity-input]')) return
    control.classList.add('coffee-quantity--enhanced')
    refreshQuantityControl(control)
  })
}

function onQuantityClick(event) {
  const button = event.target.closest && event.target.closest('[data-coffee-quantity-step]')
  if (!button || button.disabled) return
  const control = button.closest('[data-coffee-quantity-control]')
  if (!control) return
  const field = control.querySelector('[data-coffee-quantity-input]')
  if (!field || field.disabled) return
  const step = Number(button.getAttribute('data-coffee-quantity-step'))
  const { min, max } = fieldBounds(field)
  const value = nextQuantity(field.value, step, min, max)
  if (value === null) return
  event.preventDefault()
  field.value = String(value)
  // Existing live-price form listeners and other consumers observe this change.
  field.dispatchEvent(new Event('input', { bubbles: true }))
  refreshQuantityControl(control)
  field.focus()
}

function onQuantityInput(event) {
  const target = event.target
  if (!target || !target.matches || !target.matches('[data-coffee-quantity-input]')) return
  const control = target.closest('[data-coffee-quantity-control]')
  if (control) refreshQuantityControl(control)
}

function installCoffeeQuantitySteppers() {
  if (typeof document === 'undefined') return
  if (!installed) {
    installed = true
    document.addEventListener('click', onQuantityClick)
    document.addEventListener('input', onQuantityInput)
    document.addEventListener('change', onQuantityInput)
  }
  initializeCoffeeQuantitySteppers()
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', installCoffeeQuantitySteppers)
  document.addEventListener('turbolinks:load', installCoffeeQuantitySteppers)
  if (document.readyState !== 'loading') installCoffeeQuantitySteppers()
}

module.exports = {
  parseQuantity, nextQuantity, fieldBounds, refreshQuantityControl,
  initializeCoffeeQuantitySteppers, installCoffeeQuantitySteppers
}
