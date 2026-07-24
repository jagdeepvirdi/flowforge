import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getMfaStatus, mfaEnroll, mfaConfirm, mfaDisable } from '../lib/api'

export type MfaPhase = 'idle' | 'enrolling' | 'confirming' | 'backup-codes' | 'disabling'

/** MFA enrollment/confirmation/disable flow — status query, phase state machine, and mutations. */
export function useMfa() {
  const { data: mfaStatus, refetch } = useQuery({
    queryKey: ['mfa-status'],
    queryFn: getMfaStatus,
  })

  const [phase, setPhase]             = useState<MfaPhase>('idle')
  const [qrDataUrl, setQrDataUrl]     = useState('')
  const [secret, setSecret]           = useState('')
  const [uri, setUri]                 = useState('')
  const [code, setCode]               = useState('')
  const [password, setPassword]       = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [error, setError]             = useState('')
  const [copied, setCopied]           = useState(false)

  const enrollMut = useMutation({
    mutationFn: mfaEnroll,
    onSuccess: async (data) => {
      setSecret(data.secret)
      setUri(data.provisioning_uri)
      try {
        const QRCode = await import('qrcode')
        const url = await QRCode.default.toDataURL(data.provisioning_uri, { width: 200, margin: 2 })
        setQrDataUrl(url)
      } catch {
        setQrDataUrl('')
      }
      setPhase('confirming')
      setError('')
    },
    onError: (e: Error) => setError(e.message),
  })

  const confirmMut = useMutation({
    mutationFn: () => mfaConfirm(code),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes)
      setPhase('backup-codes')
      setError('')
      refetch()
    },
    onError: (e: Error) => setError(e.message),
  })

  const disableMut = useMutation({
    mutationFn: () => mfaDisable(password),
    onSuccess: () => {
      setPhase('idle')
      setPassword('')
      setError('')
      refetch()
    },
    onError: (e: Error) => setError(e.message),
  })

  const copySecret = () => {
    navigator.clipboard.writeText(secret)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return {
    enabled: mfaStatus?.mfa_enabled ?? false,
    phase, setPhase,
    qrDataUrl, secret, uri,
    code, setCode,
    password, setPassword,
    backupCodes, setBackupCodes,
    error, setError,
    copied, copySecret,
    enrollMut, confirmMut, disableMut,
  }
}
