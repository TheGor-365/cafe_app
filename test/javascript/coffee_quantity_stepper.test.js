'use strict'
const assert = require('assert')
const listeners = {}
let installedClickHandlers = 0
let priceRefreshes = 0

global.Event = class {
  constructor(type, options) { this.type = type; this.bubbles = options.bubbles }
}

function makeControl(value) {
  const attributes = { min: '1', max: '20' }
  const classes = new Set()
  const control = {
    classList: { add(name) { classes.add(name) } },
    querySelector(selector) { return selector === '[data-coffee-quantity-input]' ? field : null },
    querySelectorAll() { return [minus, plus] }
  }
  const field = {
    value, disabled: false, focused: false,
    getAttribute(name) { return attributes[name] },
    focus() { this.focused = true },
    closest(selector) { return selector === '[data-coffee-quantity-control]' ? control : null },
    matches(selector) { return selector === '[data-coffee-quantity-input]' },
    dispatchEvent(event) {
      if (event.type === 'input' && event.bubbles) {
        priceRefreshes++
        listeners.input({ target: field })
      }
    }
  }
  function button(step) {
    return {
      disabled: false,
      getAttribute() { return String(step) },
      closest(selector) { return selector === '[data-coffee-quantity-control]' ? control : null }
    }
  }
  const minus = button(-1)
  const plus = button(1)
  return { control, field, plus, minus, classes }
}

const drink = makeControl('1')
const cart = makeControl('4')
global.document = {
  readyState: 'loading',
  querySelectorAll(selector) {
    if (selector === '[data-coffee-quantity-control]') return [drink.control, cart.control]
    return []
  },
  addEventListener(name, cb) {
    if (name === 'click') installedClickHandlers++
    listeners[name] = cb
  }
}

const stepper = require('../../app/javascript/coffee_quantity_stepper')
assert.strictEqual(stepper.nextQuantity('1', -1), 1)
assert.strictEqual(stepper.nextQuantity('20', 1), 20)
assert.strictEqual(stepper.nextQuantity('19', 1), 20)
assert.strictEqual(stepper.nextQuantity('2', -1), 1)
assert.strictEqual(stepper.nextQuantity('', 1), 1)
assert.strictEqual(stepper.nextQuantity('abc', -1), 1)
assert.strictEqual(stepper.nextQuantity('-2', 1), 1)
assert.strictEqual(stepper.nextQuantity('1.5', 1), 1)
assert.strictEqual(stepper.nextQuantity('1', 5), null)
assert.strictEqual(stepper.nextQuantity('1', 1, 20, 1), null)
assert.strictEqual(stepper.parseQuantity('0002'), 2)
assert.strictEqual(stepper.parseQuantity('NaN'), null)

stepper.installCoffeeQuantitySteppers()
stepper.installCoffeeQuantitySteppers()
assert.strictEqual(installedClickHandlers, 1, 'delegate only once across Turbolinks')
assert(drink.classes.has('coffee-quantity--enhanced'))
assert(cart.classes.has('coffee-quantity--enhanced'))
assert.strictEqual(drink.minus.disabled, true, 'minus disabled at minimum')
assert.strictEqual(drink.plus.disabled, false)

function click(button) {
  let prevented = false
  listeners.click({
    target: { closest(selector) { return selector === '[data-coffee-quantity-step]' ? button : null } },
    preventDefault() { prevented = true }
  })
  return prevented
}
assert.strictEqual(click(drink.plus), true)
assert.strictEqual(drink.field.value, '2')
assert.strictEqual(drink.minus.disabled, false)
assert.strictEqual(drink.field.focused, true)
assert.strictEqual(priceRefreshes, 1, 'live price recalculates through bubbling input event')
assert.strictEqual(click(drink.minus), true)
assert.strictEqual(drink.field.value, '1')
assert.strictEqual(drink.minus.disabled, true)

cart.field.value = '20'
listeners.input({ target: cart.field })
assert.strictEqual(cart.plus.disabled, true)
assert.strictEqual(click(cart.plus), false, 'disabled plus does not change value')
assert.strictEqual(cart.field.value, '20')
assert.strictEqual(click(cart.minus), true)
assert.strictEqual(cart.field.value, '19')
assert.strictEqual(cart.plus.disabled, false)
cart.field.value = ''
listeners.input({ target: cart.field })
assert.strictEqual(click(cart.plus), true)
assert.strictEqual(cart.field.value, '1')
assert.strictEqual(priceRefreshes, 4)
console.log('Coffee quantity: boundary values, manual editing, dynamic controls and live-price events PASS')
