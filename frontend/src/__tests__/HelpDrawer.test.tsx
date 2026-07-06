import { describe, it, expect, beforeAll, afterEach } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import HelpDrawer from '../components/shared/HelpDrawer'
import { useHelp } from '../lib/useHelp'

describe('HelpDrawer open/close', () => {
  // jsdom doesn't implement <dialog>.showModal()/close() — stub them so the
  // component's imperative open-state sync doesn't throw in tests.
  beforeAll(() => {
    HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
      this.setAttribute('open', '')
    }
    HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
      this.removeAttribute('open')
    }
  })

  afterEach(() => {
    act(() => useHelp.getState().closeHelp())
  })

  it('is hidden (display: none) on first mount', () => {
    render(<HelpDrawer />)
    const dialog = screen.getByLabelText('Help', { selector: 'dialog' })
    expect(dialog).toHaveStyle({ display: 'none' })
  })

  it('becomes visible (display: flex) once openHelp() is called', async () => {
    render(<HelpDrawer />)
    act(() => useHelp.getState().openHelp('dashboard'))
    const dialog = await screen.findByLabelText('Help', { selector: 'dialog' })
    expect(dialog).toHaveStyle({ display: 'flex' })
  })

  it('goes back to hidden after closeHelp() is called', async () => {
    render(<HelpDrawer />)
    act(() => useHelp.getState().openHelp('dashboard'))
    const dialog = await screen.findByLabelText('Help', { selector: 'dialog' })
    expect(dialog).toHaveStyle({ display: 'flex' })

    act(() => useHelp.getState().closeHelp())
    expect(dialog).toHaveStyle({ display: 'none' })
  })
})
