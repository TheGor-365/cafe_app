'use strict'
const assert = require('assert')
const {
  computePriceCents,
  integerFromAttribute,
  formatCents,
  updateCoffeePrice
} = require('../../app/javascript/coffee_price_preview')

const price = computePriceCents

assert.deepStrictEqual(price(500, [60, 55, 0], 2),
  { unitCents: 615, totalCents: 1230 }, 'Medium + milk + syrup, qty 2')
assert.deepStrictEqual(price(425, [], 1),
  { unitCents: 425, totalCents: 425 }, 'plain single espresso')
assert.deepStrictEqual(price(425, [90], 3),
  { unitCents: 515, totalCents: 1545 }, 'shot extra, qty 3')
assert.deepStrictEqual(price(500, [60, 55], 20),
  { unitCents: 615, totalCents: 12300 }, 'maximum allowed quantity')
for (const qty of [0, -1, 21, 1.5, NaN, Infinity]) {
  assert.strictEqual(price(500, [], qty), null, 'reject quantity ' + qty)
}
for (const invalid of [null, -1, 1.5, NaN, Infinity, '500']) {
  assert.strictEqual(price(invalid, [], 1), null, 'reject price ' + invalid)
}
assert.strictEqual(price(500, [null], 1), null, 'missing option price is not free')
assert.strictEqual(price(500, [-1], 1), null, 'negative option price')
assert.strictEqual(price(Number.MAX_SAFE_INTEGER, [1], 2), null, 'reject overflow')
assert.strictEqual(integerFromAttribute('060'), 60)
assert.strictEqual(integerFromAttribute('0'), 0)
for (const invalid of [null, undefined, '', '-1', '1abc', '1.2']) {
  assert.strictEqual(integerFromAttribute(invalid), null)
}
assert.strictEqual(formatCents(1230), '$12.30')

// Fake DOM primitives: test actual event-free update path in Node14.
function option(priceCents) {
  return { getAttribute(name) { return name === 'data-price-cents' ? priceCents : null } }
}
const unit = { textContent: '' }
const total = { textContent: '' }
const output = { attributes: {}, setAttribute(k, v) { this.attributes[k] = v } }
const submit = { disabled: false }
const size = { selectedOptions: [option('500')] }
const milk = { selectedOptions: [option('60')] }
const syrup = { selectedOptions: [option('55')] }
const quantity = { value: '2' }
const form = {
  querySelector(query) {
    if (query.includes('product_variant_id')) return size
    if (query === '[data-coffee-price-output]') return output
    if (query === '[data-coffee-quantity]') return quantity
    if (query === '[data-coffee-unit-price]') return unit
    if (query === '[data-coffee-total-price]') return total
    if (query.includes('type="submit"')) return submit
    return null
  },
  querySelectorAll() { return [milk, syrup] },
  getAttribute() { return '425' }
}
updateCoffeePrice(form)
assert.strictEqual(unit.textContent, 'Unit: $6.15')
assert.strictEqual(total.textContent, 'Total: $12.30')
assert.strictEqual(submit.disabled, false)
quantity.value = '0'
updateCoffeePrice(form)
assert.strictEqual(total.textContent, 'Total unavailable')
assert.strictEqual(submit.disabled, true)
quantity.value = '1'
updateCoffeePrice(form)
assert.strictEqual(total.textContent, 'Total: $6.15')
assert.strictEqual(submit.disabled, false)
console.log('Coffee preview: math, data validation and DOM update PASS')
