'use strict'

const assert = require('assert')
const listeners = {}
const root = {
  children: [],
  insertBefore(node, before) {
    if (node.parentNode && node.parentNode.children) {
      node.parentNode.children.splice(node.parentNode.children.indexOf(node), 1)
    }
    const i = this.children.indexOf(before)
    this.children.splice(i < 0 ? this.children.length : i, 0, node)
    node.parentNode = this
  },
  removeChild(node) {
    this.children.splice(this.children.indexOf(node), 1)
    node.parentNode = null
  }
}
const body = {
  children: [], style: { overflow: 'auto' },
  appendChild(node) {
    if (node.parentNode && node.parentNode.children) {
      node.parentNode.children.splice(node.parentNode.children.indexOf(node), 1)
    }
    this.children.push(node)
    node.parentNode = this
  }
}
global.document = {
  readyState: 'loading', body, activeElement: null,
  addEventListener(name, callback) { listeners[name] = callback },
  createComment() { return { parentNode: null } }
}

const classes = new Set()
const classList = { add(name) { classes.add(name) }, remove(name) { classes.delete(name) } }
function focusable() {
  return { getAttribute() { return null }, getClientRects() { return [{}] },
    focus() { document.activeElement = this } }
}
const close = focusable()
const size = focusable()
const sheetAttributes = {}
const sheet = {
  querySelectorAll() { return [close, size] },
  setAttribute(name, value) { sheetAttributes[name] = value },
  removeAttribute(name) { delete sheetAttributes[name] },
  contains(node) { return [close, size].includes(node) },
  focus() { document.activeElement = this }
}
const trigger = focusable()
const details = {
  open: false, classList,
  querySelector(selector) {
    if (selector === '[data-coffee-config-panel]') return sheet
    if (selector === '.coffee-config__trigger') return trigger
    return null
  }
}
trigger.isConnected = true
trigger.closest = selector => selector === '[data-coffee-config]' ? details : null
root.children.push(details)
details.parentNode = root

const {
  closeCoffeeConfig, openCoffeeConfig, initializeCoffeeConfigPanels
} = require('../../app/javascript/coffee_config_panel')
initializeCoffeeConfigPanels()
assert.strictEqual(details.open, false, 'fallback details remains initially closed')

let prevented = false
listeners.click({
  target: { closest: selector => selector === '.coffee-config__trigger' ? trigger : null },
  preventDefault() { prevented = true }
})
assert.strictEqual(prevented, true)
assert.strictEqual(details.open, true)
assert.strictEqual(classes.has('is-modal'), true)
assert.strictEqual(details.parentNode, body, 'dialog escapes clipped card')
assert.strictEqual(sheetAttributes.role, 'dialog')
assert.strictEqual(sheetAttributes['aria-modal'], 'true')
assert.strictEqual(document.activeElement, close, 'focus enters panel')
assert.strictEqual(body.style.overflow, 'hidden')

document.activeElement = size
let wrapped = false
listeners.keydown({ key: 'Tab', shiftKey: false, preventDefault() { wrapped = true } })
assert.strictEqual(wrapped, true)
assert.strictEqual(document.activeElement, close, 'Tab cycles to first control')
let escaped = false
listeners.keydown({ key: 'Escape', preventDefault() { escaped = true } })
assert.strictEqual(escaped, true)
assert.strictEqual(details.open, false)
assert.strictEqual(details.parentNode, root, 'details restored to original card')
assert.strictEqual(document.activeElement, trigger, 'focus restored to original CTA')
assert.strictEqual(body.style.overflow, 'auto')
assert.strictEqual(sheetAttributes.role, undefined)

openCoffeeConfig(details)
listeners.click({ target: details, preventDefault() {} })
assert.strictEqual(details.open, false, 'backdrop click closes the panel')
openCoffeeConfig(details)
closeCoffeeConfig(false)
assert.strictEqual(details.open, false, 'Turbolinks can close without restoring stale focus')
assert.strictEqual(details.parentNode, root)

console.log('Coffee panel: progressive enhancement, focus, Escape, backdrop and restoration PASS')
