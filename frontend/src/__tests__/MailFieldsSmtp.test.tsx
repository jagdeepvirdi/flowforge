import { useState } from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MailFieldsSmtp from '../components/connections/MailFieldsSmtp'
import { emptyMail, type MailForm } from '../components/connections/types'

function Harness({ initial }: { initial?: Partial<MailForm> }) {
  const [form, setForm] = useState<MailForm>({ ...emptyMail(), ...initial })
  return (
    <>
      <MailFieldsSmtp form={form} setForm={setForm} />
      <div data-testid="state">{JSON.stringify({ use_tls: form.use_tls, use_ssl: form.use_ssl })}</div>
    </>
  )
}

describe('MailFieldsSmtp encryption selector', () => {
  it('defaults to STARTTLS when use_tls is true and use_ssl is false', () => {
    render(<Harness />)
    expect(screen.getByRole('radio', { name: /STARTTLS/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /SSL\/TLS/ })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: /None/ })).not.toBeChecked()
  })

  it('selects SSL/TLS when use_ssl is true, regardless of use_tls', () => {
    render(<Harness initial={{ use_tls: true, use_ssl: true }} />)
    expect(screen.getByRole('radio', { name: /SSL\/TLS/ })).toBeChecked()
  })

  it('selects None when both use_tls and use_ssl are false', () => {
    render(<Harness initial={{ use_tls: false, use_ssl: false }} />)
    expect(screen.getByRole('radio', { name: /None/ })).toBeChecked()
  })

  it('switches to SSL/TLS and clears use_tls when clicked', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole('radio', { name: /SSL\/TLS/ }))
    expect(screen.getByTestId('state')).toHaveTextContent(JSON.stringify({ use_tls: false, use_ssl: true }))
  })

  it('switches to None and clears both flags when clicked', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole('radio', { name: /None/ }))
    expect(screen.getByTestId('state')).toHaveTextContent(JSON.stringify({ use_tls: false, use_ssl: false }))
  })

  it('switches back to STARTTLS from SSL/TLS', async () => {
    const user = userEvent.setup()
    render(<Harness initial={{ use_tls: false, use_ssl: true }} />)
    await user.click(screen.getByRole('radio', { name: /STARTTLS/ }))
    expect(screen.getByTestId('state')).toHaveTextContent(JSON.stringify({ use_tls: true, use_ssl: false }))
  })
})
