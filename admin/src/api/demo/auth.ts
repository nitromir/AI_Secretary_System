import type { DemoRoute } from './types'

export const authRoutes: DemoRoute[] = [
  {
    method: 'POST',
    pattern: /^\/admin\/auth\/login$/,
    handler: ({ body }) => {
      const { username, password } = body as { username: string; password: string }
      if (username === 'admin' && password === 'admin') {
        const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
        const payload = btoa(JSON.stringify({
          sub: 'admin',
          role: 'admin',
          exp: Math.floor(Date.now() / 1000) + 86400,
          iat: Math.floor(Date.now() / 1000),
          demo: true,
        }))
        const signature = btoa('demo-signature')
        return { access_token: `${header}.${payload}.${signature}` }
      }
      throw new Error('Invalid credentials')
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/auth\/logout$/,
    handler: () => ({ status: 'ok' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/auth\/refresh$/,
    handler: () => {
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
      const payload = btoa(JSON.stringify({
        sub: 'admin',
        role: 'admin',
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
        demo: true,
      }))
      const signature = btoa('demo-signature')
      return { access_token: `${header}.${payload}.${signature}` }
    },
  },
]
