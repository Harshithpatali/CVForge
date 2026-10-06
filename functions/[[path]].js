export async function onRequest(context) {
  const url = new URL(context.request.url)
  if (!url.pathname.startsWith('/api')) return context.next()

  const apiBase = context.env.CVFORGE_API_URL
  if (!apiBase) {
    return Response.json(
      { detail: 'CVForge backend is not configured. Set CVFORGE_API_URL in Cloudflare Pages.' },
      { status: 503 },
    )
  }

  const upstream = new URL(
    url.pathname.slice('/api'.length) + url.search,
    apiBase.replace(/\/$/, '') + '/',
  )

  const headers = new Headers(context.request.headers)
  headers.delete('host')

  const request = new Request(upstream, {
    method: context.request.method,
    headers,
    body: ['GET', 'HEAD'].includes(context.request.method)
      ? undefined
      : context.request.body,
    redirect: 'follow',
  })

  return fetch(request)
}