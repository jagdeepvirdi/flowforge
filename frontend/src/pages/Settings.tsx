import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import TopBar from '../components/shared/TopBar'
import PageIntro from '../components/shared/PageIntro'
import ChangePasswordCard from '../components/settings/ChangePasswordCard'
import MfaCard from '../components/settings/MfaCard'
import GoogleOAuthCard from '../components/settings/GoogleOAuthCard'
import Microsoft365Card from '../components/settings/Microsoft365Card'
import AiOllamaCard from '../components/settings/AiOllamaCard'
import RetentionCard from '../components/settings/RetentionCard'
import YamlCard from '../components/settings/YamlCard'
import DocsCard from '../components/settings/DocsCard'
import { getSetupStatus } from '../lib/api'

type Tab = 'account' | 'email' | 'ai' | 'system' | 'docs'

const TABS: { id: Tab; label: string }[] = [
  { id: 'account', label: 'Account' },
  { id: 'email', label: 'Email' },
  { id: 'ai', label: 'AI' },
  { id: 'system', label: 'System' },
  { id: 'docs', label: 'Docs' },
]

export default function Settings() {
  const [tab, setTab] = useState<Tab>('account')

  const { data: status, isLoading } = useQuery({
    queryKey: ['setup-status'],
    queryFn: getSetupStatus,
    staleTime: 30_000,
  })

  return (
    <>
      <TopBar crumbs={['Workspace', 'Settings']} helpTopic="settings" />
      <div className="scroll max-w-[680px]">
        <PageIntro page="settings" />
        <div className="page-h">
          <h1>Settings</h1>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border mb-5">
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => setTab(t.id)} className={`bg-transparent border-none py-2.5 px-4 text-[13px] cursor-pointer -mb-px border-b-2 ${active ? 'text-accent font-semibold border-b-accent' : 'text-text-3 font-medium border-b-transparent'}`}>
                {t.label}
              </button>
            )
          })}
        </div>

        <div className="flex flex-col gap-3.5">

          {tab === 'account' && (
            <>
              <ChangePasswordCard />
              <MfaCard />
            </>
          )}

          {tab === 'email' && (
            <>
              <GoogleOAuthCard status={status} isLoading={isLoading} />
              <Microsoft365Card status={status} isLoading={isLoading} />
            </>
          )}

          {tab === 'ai' && (
            <AiOllamaCard status={status} isLoading={isLoading} />
          )}

          {tab === 'system' && (
            <>
              <RetentionCard />
              <YamlCard />
            </>
          )}

          {tab === 'docs' && (
            <DocsCard />
          )}

        </div>
      </div>
    </>
  )
}
