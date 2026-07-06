import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { login, getMe } from '../lib/api'
import { useAuth } from '../lib/auth'

function mockFetchOnce(init: {
  ok: boolean
  status?: number
  json?: () => Promise<unknown>
}) {
  const response = {
    ok: init.ok,
    status: init.status ?? (init.ok ? 200 : 500),
    json: init.json ?? (() => Promise.resolve({})),
  } as Response
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response)))
  return response
}

describe('api request()', () => {
  beforeEach(() => {
    useAuth.getState().clearToken()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.history.pushState({}, '', '/')
  })

  it('sends method, URL, and JSON body for a POST call', async () => {
    mockFetchOnce({ ok: true, json: () => Promise.resolve({ token: 'abc' }) })
    await login('admin', 'secret')
    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toBe('/api/auth/login')
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ username: 'admin', password: 'secret' }))
    expect(init.headers['Content-Type']).toBe('application/json')
  })

  it('omits the Authorization header when there is no token', async () => {
    mockFetchOnce({ ok: true, json: () => Promise.resolve({}) })
    await getMe()
    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers['Authorization']).toBeUndefined()
  })

  it('adds a Bearer Authorization header when a token is set', async () => {
    useAuth.getState().setToken('tok-123')
    mockFetchOnce({ ok: true, json: () => Promise.resolve({}) })
    await getMe()
    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers['Authorization']).toBe('Bearer tok-123')
  })

  it('resolves with the parsed JSON body on a 2xx response', async () => {
    mockFetchOnce({ ok: true, json: () => Promise.resolve({ id: 'u1', username: 'admin' }) })
    const me = await getMe()
    expect(me).toEqual({ id: 'u1', username: 'admin' })
  })

  it('throws the server error message on a non-2xx response', async () => {
    mockFetchOnce({ ok: false, status: 400, json: () => Promise.resolve({ error: 'Invalid credentials' }) })
    await expect(login('admin', 'wrong')).rejects.toThrow('Invalid credentials')
  })

  it('falls back to "HTTP <status>" when the error body cannot be parsed', async () => {
    mockFetchOnce({ ok: false, status: 500, json: () => Promise.reject(new Error('not json')) })
    await expect(getMe()).rejects.toThrow('HTTP 500')
  })

  it('does not swallow a JSON parse failure on a successful response', async () => {
    // A truncated/empty body on a 2xx response must surface as a real rejection,
    // not silently resolve to `{}` — see api.ts request()'s res.json() comment.
    mockFetchOnce({ ok: true, json: () => Promise.reject(new SyntaxError('Unexpected end of JSON input')) })
    await expect(getMe()).rejects.toThrow('Unexpected end of JSON input')
  })

  it('clears the token and throws on a 401 response', async () => {
    window.history.pushState({}, '', '/login')
    useAuth.getState().setToken('stale-token')
    mockFetchOnce({ ok: false, status: 401, json: () => Promise.resolve({ error: 'Session expired' }) })
    await expect(getMe()).rejects.toThrow('Session expired')
    expect(useAuth.getState().token).toBeNull()
  })

  it('defaults the 401 error message to "Unauthorized" when the body has no error field', async () => {
    window.history.pushState({}, '', '/login')
    mockFetchOnce({ ok: false, status: 401, json: () => Promise.resolve({}) })
    await expect(getMe()).rejects.toThrow('Unauthorized')
  })
})
