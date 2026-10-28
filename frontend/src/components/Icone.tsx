import type { ReactNode } from 'react'
import type { Pagina } from '../hooks/useNavegacao'

export type NomeIcone = Pagina | 'menu' | 'fechar' | 'enviar' | 'sair' | 'mais'

// Traços simples em 24x24, desenhados aqui para não depender de biblioteca de ícones.
const DESENHOS: Record<NomeIcone, ReactNode> = {
  inicio: (
    <>
      <path d="M3.5 10.5 12 3.5l8.5 7" />
      <path d="M5.5 9v11.5h13V9" />
      <path d="M10 20.5v-6h4v6" />
    </>
  ),
  documentos: (
    <>
      <path d="M14 3.5H6.5a1 1 0 0 0-1 1v15a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V8z" />
      <path d="M14 3.5V8h4.5" />
      <path d="M9 13h6M9 16.5h4" />
    </>
  ),
  contas: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
      <path d="M8 14h3" />
    </>
  ),
  despesas: (
    <>
      <path d="M6 3.5h12v17l-3-2-3 2-3-2-3 2z" />
      <path d="M9 8.5h6M9 12h6M9 15.5h3" />
    </>
  ),
  assistente: (
    <>
      <path d="M4 5.5h16v10.5H9.5L4 20z" />
      <path d="M8.5 10.75h.01M12 10.75h.01M15.5 10.75h.01" />
    </>
  ),
  relatorios: (
    <>
      <path d="M4 20h16" />
      <path d="M7.5 16.5v-5M12 16.5v-9M16.5 16.5v-7" />
    </>
  ),
  fornecedores: (
    <>
      <path d="M3 6.5h11v9.5H3z" />
      <path d="M14 10h3.8l3.2 3.2V16H14" />
      <circle cx="7" cy="18" r="1.8" />
      <circle cx="17" cy="18" r="1.8" />
    </>
  ),
  categorias: (
    <>
      <path d="M3.5 12V4.5H11l9.5 9.5-7.5 7.5z" />
      <circle cx="7.75" cy="8.75" r="1.25" />
    </>
  ),
  equipe: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <circle cx="17" cy="9" r="2.3" />
      <path d="M16 14.2a4.5 4.5 0 0 1 5 4.3" />
    </>
  ),
  menu: <path d="M4 6.5h16M4 12h16M4 17.5h16" />,
  fechar: <path d="M6 6l12 12M18 6 6 18" />,
  enviar: (
    <>
      <path d="M12 15V4.5M7.5 9 12 4.5 16.5 9" />
      <path d="M4.5 14.5v4.5a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1v-4.5" />
    </>
  ),
  sair: (
    <>
      <path d="M14.5 4.5h4a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-4" />
      <path d="M10 16l4-4-4-4M14 12H4.5" />
    </>
  ),
  mais: <path d="M12 5v14M5 12h14" />,
}

export function Icone({ nome, tamanho = 20 }: { nome: NomeIcone; tamanho?: number }) {
  return (
    <svg
      className="icone"
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {DESENHOS[nome]}
    </svg>
  )
}
