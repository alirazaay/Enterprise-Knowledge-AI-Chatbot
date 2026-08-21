import { useAuth } from '../hooks/useAuth'

export default function DashboardPage() {
  const { user, logout } = useAuth()

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">Authenticated workspace</p>
          <h1 className="mt-3 text-3xl font-semibold">Enterprise Knowledge AI</h1>
          <p className="mt-3 text-slate-400">Welcome, {user?.name}. Knowledge features will be introduced in later phases.</p>
        </div>
        <button className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400" onClick={logout}>
          Log out
        </button>
      </div>
    </main>
  )
}
