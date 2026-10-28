import { useEffect } from 'react'
import './App.css'
import { AreaLogada } from './components/AreaLogada'
import { Cabecalho, Rodape } from './components/Cabecalho'
import { TelaAcesso } from './components/TelaAcesso'
import { useSessao } from './hooks/useSessao'
import { useStatusSistema } from './hooks/useStatusSistema'
import { useTema } from './hooks/useTema'

function App() {
  const status = useStatusSistema()
  const sessao = useSessao()
  const tema = useTema()
  const usuarioId = sessao.usuario?.id
  const { atualizar: atualizarStatus } = status

  // O nome do modelo de IA só vem para quem está logado: ao entrar ou sair, o status é consultado de novo.
  useEffect(() => {
    if (usuarioId !== undefined) atualizarStatus()
  }, [usuarioId, atualizarStatus])

  const sair = () => void sessao.sair()

  let tela
  if (sessao.usuario && !sessao.verificando) {
    // A área logada monta a própria tela (barra lateral). key: ao trocar de usuário, todo o estado é descartado.
    tela = (
      <AreaLogada
        key={sessao.usuario.id}
        usuario={sessao.usuario}
        status={status}
        tema={tema}
        onSair={sair}
        onSessaoExpirada={sessao.sessaoExpirou}
      />
    )
  } else {
    tela = (
      <>
        <Cabecalho status={status} tema={tema} usuario={null} onSair={sair} />
        <main className="conteudo">
          {sessao.verificando ? <p className="carregando-pagina">Carregando…</p> : <TelaAcesso sessao={sessao} />}
        </main>
        <Rodape />
      </>
    )
  }

  return (
    <div className="pagina">
      {status.backend?.modo_demonstracao && (
        <p className="faixa-demonstracao" role="note">
          Demonstração · todos os dados são fictícios, criados para apresentar o sistema
        </p>
      )}
      {tela}
    </div>
  )
}

export default App
