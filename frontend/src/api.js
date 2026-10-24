let token = sessionStorage.getItem('alfa-token') || ''
export const setToken = (value) => {
  token = value || ''
  if (token) sessionStorage.setItem('alfa-token', token)
  else sessionStorage.removeItem('alfa-token')
}
export const hasToken = () => Boolean(token)
export async function api(path, { method = 'GET', data, key } = {}) {
  const multipart = data instanceof FormData
  const response = await fetch('/api/v1/' + path, {
    method,
    headers: {
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(data && !multipart ? { 'Content-Type': 'application/json' } : {}),
      ...(key ? { 'Idempotency-Key': key } : {}),
    },
    ...(data ? { body: multipart ? data : JSON.stringify(data) } : {}),
  })
  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message =
      body.detail ||
      Object.values(body).flat().join(' ') ||
      'Не удалось выполнить запрос. Повторите попытку.'
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return body
}
export async function documentBlob(applicationId, documentId) {
  const response = await fetch(
    `/api/v1/applications/${applicationId}/documents/${documentId}/download/`,
    { headers: { Authorization: `Token ${token}` } },
  )
  if (!response.ok)
    throw new Error(
      'Не удалось скачать документ. Обновите сессию и повторите попытку.',
    )
  return response.blob()
}
export const draftPayload = (draft) => ({
  product_id: draft.productId,
  amount: draft.amount,
  term_months: draft.months,
  purpose: draft.purpose,
  monthly_revenue: draft.revenue,
  current_monthly_payments: draft.payments,
})
export const normalizeApplication = (item) => ({
  ...item,
  productId: item.product_id,
  months: item.term_months,
  revenue: item.monthly_revenue,
  payments: item.current_monthly_payments,
  company: item.company_name,
  companyData: item.company,
  score: item.scoring?.score ?? null,
  risk: item.scoring?.grade ? `Рейтинг ${item.scoring.grade}` : 'Нет оценки',
  decision: ['APPROVED', 'REJECTED', 'CANCELLED'].includes(item.status)
    ? item.status_label
    : '',
})
