export type Course = { id: number; title: string; status: string; hours: string; content: string; registration_url: string; source_url: string; approved: boolean; pending: Partial<Course> | null; synced_at: string }
export type Lead = { id: number; name: string; channel: string; stage: string; course_id: number | null; priority: number; handoff: boolean; owner: string; notes: string; next_action: string; profile: Record<string,string>; sentiment: string; sentiment_reason: string; summary: string; updated_at: string }
export type Message = { id: number; role: string; text: string; delivery: string; created_at: string }
export type Status = { telegram_configured: boolean; llm_configured: boolean; llm_provider?: string; llm_model?: string; llm_runtime?: { successful_calls: number; failed_calls: number; last_success_at: string | null; last_failure_at: string | null; last_error_code: number | null; last_error_type: string | null } }
export function providerState(status: Status) {
  if (!status.llm_configured) return { ok:false, label:'Pendiente', detail:'Requiere credenciales y modelo' }
  const runtime=status.llm_runtime
  const success=runtime?.last_success_at ? Date.parse(runtime.last_success_at) : 0
  const failure=runtime?.last_failure_at ? Date.parse(runtime.last_failure_at) : 0
  if (failure && failure>=success) {
    const code=runtime?.last_error_code
    const detail=code===404 ? 'Modelo no disponible (HTTP 404)' : code===429 ? 'Límite de cuota o solicitudes (HTTP 429)' : code ? `Última llamada fallida (HTTP ${code})` : 'La última llamada al modelo falló'
    return { ok:false, label:'Usando respaldo', detail }
  }
  if (success) return { ok:true, label:'Última llamada correcta', detail:'Hay una respuesta del modelo verificada' }
  return { ok:false, label:'Sin verificar', detail:'Credenciales presentes; aún no hay llamadas verificadas' }
}
export const token = () => sessionStorage.getItem('ctt_token') || ''
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}`, ...options.headers } })
  if (!response.ok) {
    if (response.status === 401 && !path.includes('/auth/')) { sessionStorage.removeItem('ctt_token'); window.dispatchEvent(new Event('session-expired')) }
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No se pudo completar la operación')
  }
  return response.json()
}
export const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })
export const stages: Record<string,string> = { nuevo: 'Nuevo', interesado: 'Interesado', solicita_inscripcion: 'Solicita inscripción', seguimiento: 'En seguimiento', inscrito: 'Inscrito', cerrado: 'Cerrado' }
export const sentiments: Record<string,string> = { interesado: 'Interesado', dudoso: 'Con dudas', frustrado: 'Frustrado', caliente: 'Lead caliente' }
export function date(value: string) { return new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : value+'Z').toLocaleString('es-EC', { timeZone: 'America/Guayaquil', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) }
