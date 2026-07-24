import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { changePassword } from '../lib/api'

export function useChangePassword() {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState(false)

  const mut = useMutation({
    mutationFn: () => changePassword({ current_password: form.current_password, new_password: form.new_password }),
    onSuccess: () => {
      setSuccess(true)
      setError('')
      setForm({ current_password: '', new_password: '', confirm: '' })
    },
    onError: (e: Error) => { setError(e.message); setSuccess(false) },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (form.new_password.length < 8) { setError('New password must be at least 8 characters'); return }
    if (form.new_password !== form.confirm) { setError('Passwords do not match'); return }
    mut.mutate()
  }

  return { form, setForm, error, success, mut, handleSubmit }
}
