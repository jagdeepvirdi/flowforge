import { create } from 'zustand'

interface HelpState {
  open:       boolean
  topic:      string
  openHelp:   (topic?: string) => void
  closeHelp:  () => void
}

export const useHelp = create<HelpState>(set => ({
  open:      false,
  topic:     'dashboard',
  openHelp:  (topic = 'dashboard') => set({ open: true, topic }),
  closeHelp: () => set({ open: false }),
}))
