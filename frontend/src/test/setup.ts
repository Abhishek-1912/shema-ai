// Runs once before every test file.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Remove whatever a test rendered, so the next test starts with an empty page.
afterEach(() => {
  cleanup()
})

// jsdom (the fake browser used in tests) does not implement scrolling.
Element.prototype.scrollIntoView = vi.fn()
