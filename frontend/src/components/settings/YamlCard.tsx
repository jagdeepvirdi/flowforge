import { CodeBlock } from './common'

export default function YamlCard() {
  return (
    <div className="card flex flex-col gap-3">
      <div className="text-[13px] font-semibold text-text-primary">Pipeline YAML Export / Import</div>
      <p className="text-[13px] text-text-muted m-0">Export or import pipeline definitions as YAML.</p>
      <CodeBlock>flowforge export "My Pipeline" --output pipeline.yaml</CodeBlock>
      <CodeBlock>flowforge import pipeline.yaml</CodeBlock>
    </div>
  )
}
