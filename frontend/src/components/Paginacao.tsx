interface PaginacaoProps {
  deslocamento: number
  limite: number
  total: number
  onMudar: (deslocamento: number) => void
}

export function Paginacao({ deslocamento, limite, total, onMudar }: PaginacaoProps) {
  if (total <= limite) return null
  const inicio = deslocamento + 1
  const fim = Math.min(deslocamento + limite, total)

  return (
    <nav className="paginacao" aria-label="Paginação">
      <button
        type="button"
        className="botao botao--secundario"
        disabled={deslocamento === 0}
        onClick={() => onMudar(Math.max(0, deslocamento - limite))}
      >
        Anterior
      </button>
      <span>
        {inicio}–{fim} de {total}
      </span>
      <button
        type="button"
        className="botao botao--secundario"
        disabled={fim >= total}
        onClick={() => onMudar(deslocamento + limite)}
      >
        Próxima
      </button>
    </nav>
  )
}
