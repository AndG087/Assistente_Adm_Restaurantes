import { useRef, useState } from 'react'
import { useArea } from '../contexto'

/**
 * Executa uma ação de botão (salvar, excluir, pagar…) e guarda a mensagem de erro.
 *
 * Enquanto uma ação está em andamento, outra chamada é ignorada: um clique duplo
 * não envia o mesmo pedido duas vezes. `ocupado` serve para desabilitar os botões.
 */
export function useAcao() {
  const { mensagemDeErro } = useArea()
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  // A ref muda na hora; o estado só muda no próximo desenho da tela.
  const emAndamento = useRef(false)

  async function executar(acao: () => Promise<unknown>, depois?: () => void): Promise<boolean> {
    if (emAndamento.current) return false
    emAndamento.current = true
    setOcupado(true)
    setErro(null)
    try {
      await acao()
      depois?.()
      return true
    } catch (e) {
      setErro(mensagemDeErro(e))
      return false
    } finally {
      emAndamento.current = false
      setOcupado(false)
    }
  }

  return { executar, ocupado, erro, setErro }
}
