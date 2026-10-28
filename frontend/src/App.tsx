import './App.css'
import { AreaLogada } from './components/AreaLogada'
import { Cabecalho } from './components/Cabecalho'
import { TelaAcesso } from './components/TelaAcesso'
import { useSessao } from './hooks/useSessao'
import { useStatusSistema } from './hooks/useStatusSistema'

function App() {
  const status = useStatusSistema()
  const sessao = useSessao()

  let conteudo
  if (sessao.verificando) {
    conteudo = <p className="carregando-pagina">Carregando…</p>
  } else if (!sessao.usuario) {
    conteudo = <TelaAcesso sessao={sessao} />
  } else {
    // key: ao trocar de usuário, todo o estado da área logada (restaurantes, conversa) é descartado.
    conteudo = (
      <AreaLogada
        key={sessao.usuario.id}
        statusIA={status.ia}
        onFalhaIA={status.atualizar}
        onSessaoExpirada={sessao.sessaoExpirou}
      />
    )
  }

  return (
    <div className="pagina">
      {status.backend?.modo_demonstracao && (
        <p className="faixa-demonstracao" role="note">
          Demonstração · todos os dados são fictícios, criados para apresentar o sistema
        </p>
      )}
      <Cabecalho status={status} usuario={sessao.usuario} onSair={() => void sessao.sair()} />
      <main className="conteudo">{conteudo}</main>
      <footer className="rodape">Executado localmente · Nenhum dado é enviado para serviços externos</footer>
    </div>
  )
}

export default App
