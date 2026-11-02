/*
 * Progressive-enhancement dialog for the legacy Rails storefront.
 * Native <details> stays usable when JS or Webpacker fails.
 * Move the open details element to <body> to escape legacy card overflow
 * and hover-transform stacking contexts, then restore it on close.
 */
'use strict'

const { initializeCoffeePricePreviews } = require('./coffee_price_preview')

let activePanel = null
let handlersInstalled = false

const FOCUS_SELECTOR = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'

function focusableElements(sheet) {
  return Array.from(sheet.querySelectorAll(FOCUS_SELECTOR)).filter(node => {
    return node.getAttribute('aria-hidden') !== 'true' &&
      node.getAttribute('type') !== 'hidden' &&
      node.getAttribute('tabindex') !== '-1' &&
      node.getClientRects().length > 0
  })
}

function closeCoffeeConfig(restoreFocus = true) {
  if (!activePanel) return
  const state = activePanel
  activePanel = null

  state.inerted.forEach(node => node.removeAttribute('inert'))
  state.details.open = false
  state.details.classList.remove('is-modal')
  state.sheet.removeAttribute('role')
  state.sheet.removeAttribute('aria-modal')
  state.anchor.parentNode.insertBefore(state.details, state.anchor)
  state.anchor.parentNode.removeChild(state.anchor)
  document.body.style.overflow = state.bodyOverflow

  if (restoreFocus && state.trigger.isConnected) state.trigger.focus()
}

function openCoffeeConfig(details) {
  if (activePanel && activePanel.details === details) return
  if (activePanel) closeCoffeeConfig(false)

  const sheet = details.querySelector('[data-coffee-config-panel]')
  const trigger = details.querySelector('.coffee-config__trigger')
  if (!sheet || !trigger || !details.parentNode) return

  const anchor = document.createComment('coffee dialog return point')
  details.parentNode.insertBefore(anchor, details)
  const bodyOverflow = document.body.style.overflow
  document.body.appendChild(details)
  details.classList.add('is-modal')
  details.open = true
  sheet.setAttribute('role', 'dialog')
  sheet.setAttribute('aria-modal', 'true')
  document.body.style.overflow = 'hidden'
  // Keep assistive technology and keyboard navigation inside the modal.
  const inerted = Array.from(document.body.children).filter(node =>
    node !== details && node.nodeType === 1 && !node.hasAttribute('inert'))
  inerted.forEach(node => node.setAttribute('inert', ''))

  activePanel = { details, sheet, trigger, anchor, bodyOverflow, inerted }
  // AJAX menu search can inject fresh forms after the initial page load.
  initializeCoffeePricePreviews()
  const focusables = focusableElements(sheet)
  if (focusables.length) focusables[0].focus()
  else { sheet.setAttribute('tabindex', '-1'); sheet.focus() }
}

function onCoffeePanelClick(event) {
  const trigger = event.target.closest && event.target.closest('.coffee-config__trigger')
  if (trigger) {
    const details = trigger.closest('[data-coffee-config]')
    if (!details) return
    event.preventDefault()
    openCoffeeConfig(details)
    return
  }

  if (!activePanel) return
  if (event.target.closest && event.target.closest('[data-coffee-config-close]')) {
    event.preventDefault()
    closeCoffeeConfig()
  } else if (event.target === activePanel.details) {
    closeCoffeeConfig()
  }
}

function onCoffeePanelKeydown(event) {
  if (!activePanel) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeCoffeeConfig()
    return
  }
  if (event.key !== 'Tab') return

  const focusables = focusableElements(activePanel.sheet)
  if (focusables.length === 0) {
    event.preventDefault()
    activePanel.sheet.focus()
    return
  }
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  if (event.shiftKey && (document.activeElement === first || !activePanel.sheet.contains(document.activeElement))) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (document.activeElement === last || !activePanel.sheet.contains(document.activeElement))) {
    event.preventDefault()
    first.focus()
  }
}

function initializeCoffeeConfigPanels() {
  if (typeof document === 'undefined' || handlersInstalled) return
  handlersInstalled = true
  document.addEventListener('click', onCoffeePanelClick)
  document.addEventListener('keydown', onCoffeePanelKeydown)
  document.addEventListener('turbolinks:before-cache', () => closeCoffeeConfig(false))
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', initializeCoffeeConfigPanels)
  document.addEventListener('turbolinks:load', initializeCoffeeConfigPanels)
  if (document.readyState !== 'loading') initializeCoffeeConfigPanels()
}

module.exports = { focusableElements, closeCoffeeConfig, openCoffeeConfig, initializeCoffeeConfigPanels }
