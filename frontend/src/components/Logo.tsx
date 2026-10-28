/** Marca do Caderninho: uma página de caderno com espiral, nas cores do cardápio (verde-escuro e verde médio). */
export function Logo({ tamanho = 40 }: { tamanho?: number }) {
  return (
    <svg
      className="logo"
      width={tamanho}
      height={tamanho}
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="6" y="6" width="28" height="30" rx="4" fill="#fbfdf9" stroke="#2e4a2c" strokeWidth="2.5" />
      <path d="M12.5 10v22" stroke="#83a576" strokeWidth="1.5" />
      <path d="M16 16h13M16 22h13M16 28h8" stroke="#2e4a2c" strokeWidth="2.2" strokeLinecap="round" />
      <g fill="#2e4a2c">
        <circle cx="14" cy="6" r="2.4" />
        <circle cx="20" cy="6" r="2.4" />
        <circle cx="26" cy="6" r="2.4" />
      </g>
    </svg>
  )
}
