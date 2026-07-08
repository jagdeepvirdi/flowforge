import Spinner from './Spinner'

export default function RouteFallback() {
  return (
    <div className="flex items-center justify-center w-full h-full min-h-[50vh]">
      <Spinner size={28} />
    </div>
  )
}
