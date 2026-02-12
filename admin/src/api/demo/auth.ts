import type { DemoRoute } from './types'

const demoRole = import.meta.env.VITE_DEMO_ROLE || 'admin'
const demoDeploymentMode = import.meta.env.VITE_DEMO_DEPLOYMENT_MODE || 'full'

function createDemoToken(username: string): { access_token: string } {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({
    sub: username,
    role: demoRole,
    exp: Math.floor(Date.now() / 1000) + 86400,
    iat: Math.floor(Date.now() / 1000),
    demo: true,
  }))
  const signature = btoa('demo-signature')
  return { access_token: `${header}.${payload}.${signature}` }
}

export const authRoutes: DemoRoute[] = [
  {
    method: 'POST',
    pattern: /^\/admin\/auth\/login$/,
    handler: ({ body }) => {
      const { username, password } = body as { username: string; password: string }
      if (
        (username === 'admin' && password === 'admin') ||
        (username === 'demo' && password === 'demo')
      ) {
        return createDemoToken(username)
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
    handler: () => createDemoToken('admin'),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/auth\/me$/,
    handler: () => ({
      username: 'admin',
      role: demoRole,
      deployment_mode: demoDeploymentMode,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/deployment-mode$/,
    handler: () => ({ mode: demoDeploymentMode }),
  },
]
