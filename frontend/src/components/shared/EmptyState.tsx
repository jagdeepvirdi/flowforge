interface Props { message: string; action?: React.ReactNode }

export default function EmptyState({ message, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-text-muted text-sm mb-4">{message}</p>
      {action}
    </div>
  )
}
