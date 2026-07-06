import '@testing-library/jest-dom'

// jsdom has no ResizeObserver — Recharts' <ResponsiveContainer> needs one to
// mount at all, even in tests that never resize anything.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver
