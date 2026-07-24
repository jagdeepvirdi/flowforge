import { BrainCircuit } from 'lucide-react'
import Sk from '../shared/Skeleton'
import { StatusBadge, CodeBlock, InlineCode } from './common'
import type { SetupStatus } from '../../lib/api'

export default function AiOllamaCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[7px] text-[13px] font-semibold text-text-primary">
          <BrainCircuit size={15} className="text-text-muted" />
          AI Features
        </div>
        {isLoading
          ? <Sk h={13} style={{ width: 120 }} />
          : status && (
            <StatusBadge
              ok={status.ai.enabled}
              label={status.ai.enabled ? `Enabled · ${status.ai.ollama_url}` : 'Disabled'}
            />
          )
        }
      </div>
      <p className="text-[13px] text-text-muted m-0">
        SQL Explain, SQL Optimize, Data Profiler, Chart Generator, and Pipeline Failure Diagnosis all
        route through a local <InlineCode>Ollama</InlineCode> instance by default — no data leaves your
        machine and there is no API cost. If Claude or Gemini is configured below, they're used as an
        automatic fallback only when Ollama is unreachable (Claude first, then Gemini).
        Set <InlineCode>FLOWFORGE_AI_ENABLED=false</InlineCode> to hide all AI buttons and disable all AI endpoints.
      </p>
      {status && !status.ai.enabled && (
        <div className="py-2 px-3 bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.15)] rounded-r-sm text-xs text-text-2">
          AI is currently disabled. Remove or change the env var below and restart to re-enable.
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <CodeBlock>FLOWFORGE_AI_ENABLED=true   # set to false to disable all AI features</CodeBlock>
        <CodeBlock>OLLAMA_URL=http://localhost:11434</CodeBlock>
        <CodeBlock>OLLAMA_CHART_MODEL=llama3.2:3b   # model for chart & profile tasks</CodeBlock>
        <CodeBlock>OLLAMA_QUERY_MODEL=llama3.2:3b   # model for explain/optimize/diagnose</CodeBlock>
      </div>

      <div className="h-px bg-border my-0.5" />

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-medium text-text-primary">Claude / Gemini fallback &amp; ai_analyze providers</span>
        </div>
        <p className="text-[13px] text-text-muted m-0">
          Configuring a key here enables it as the Ollama-unreachable fallback above, and makes it
          selectable in the <InlineCode>ai_analyze</InlineCode> pipeline step via
          <InlineCode>provider: "claude"</InlineCode> or <InlineCode>provider: "gemini"</InlineCode>.
        </p>

        <div className="flex items-center justify-between mt-1">
          <span className="text-[13px] text-text-2">Claude API (Anthropic)</span>
          {isLoading
            ? <Sk h={13} style={{ width: 90 }} />
            : status && (
              <StatusBadge
                ok={status.ai.claude.configured}
                label={status.ai.claude.configured ? 'Key configured' : 'Not configured'}
              />
            )
          }
        </div>
        <CodeBlock>ANTHROPIC_API_KEY=   # requires: pip install anthropic</CodeBlock>

        <div className="flex items-center justify-between mt-1">
          <span className="text-[13px] text-text-2">Gemini API (Google, free tier)</span>
          {isLoading
            ? <Sk h={13} style={{ width: 90 }} />
            : status && (
              <StatusBadge
                ok={status.ai.gemini.configured}
                label={status.ai.gemini.configured ? `Key configured · ${status.ai.gemini.model}` : 'Not configured'}
              />
            )
          }
        </div>
        <CodeBlock>GEMINI_API_KEY=   # free tier: aistudio.google.com/apikey</CodeBlock>
        <CodeBlock>GEMINI_QUERY_MODEL=gemini-2.5-flash</CodeBlock>
      </div>
    </div>
  )
}
