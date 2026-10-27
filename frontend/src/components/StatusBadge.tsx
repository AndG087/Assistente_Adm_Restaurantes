export type NivelStatus = 'ok' | 'alerta' | 'erro' | 'verificando'

interface StatusBadgeProps {
  rotulo: string
  nivel: NivelStatus
  descricao: string
}

export function StatusBadge({ rotulo, nivel, descricao }: StatusBadgeProps) {
  return (
    <div className={`status-badge status-badge--${nivel}`} role="status">
      <span className="status-badge__ponto" aria-hidden="true" />
      <span className="status-badge__rotulo">{rotulo}</span>
      <span className="status-badge__descricao">{descricao}</span>
    </div>
  )
}
