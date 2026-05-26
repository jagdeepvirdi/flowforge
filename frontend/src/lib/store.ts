import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ProjectStore {
  activeProjectId: string | null
  setActiveProjectId: (id: string | null) => void

  theme: 'dark' | 'light'
  toggleTheme: () => void
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      activeProjectId: null,
      setActiveProjectId: (id) => set({ activeProjectId: id }),

      theme: 'dark',

      toggleTheme: () =>
        set((state) => ({
          theme: state.theme === 'dark' ? 'light' : 'dark',
        })),
    }),
    { name: 'ff-active-project' },
  ),
)