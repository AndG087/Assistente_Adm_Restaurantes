"""Cria uma demonstração com dados FICTÍCIOS de um bar e restaurante.

Uso (a partir de backend/, com o banco de demonstração em DATABASE_URL):

    python -m scripts.criar_demonstracao --nome "Nome do Restaurante"

Normalmente é chamado por iniciar_demonstracao.ps1, que já configura tudo.
O nome do restaurante é informado na hora (não fica no código, que é público no GitHub).

Por segurança, só roda em um banco cujo nome termine em "_demo": o script APAGA todos os dados dele.
"""

import argparse
import random
import shutil
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registra as tabelas)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.models import Usuario
from app.schemas.conta_pagar import ContaPagarCreate
from app.schemas.despesa import DespesaCreate
from app.schemas.fornecedor import FornecedorCreate
from app.services import (
    auth_service,
    categoria_service,
    conta_pagar_service,
    despesa_service,
    documento_service,
    fornecedor_service,
    restaurante_service,
)
from tests.arquivos import pdf_com_texto, png_com_texto

EMAIL = "demo@exemplo.com"
SENHA = "demonstracao"
MESES_DE_HISTORICO = 6

# Fornecedores inventados. Só o primeiro tem CNPJ: o de exemplo, usado em materiais didáticos.
FORNECEDORES = {
    "chopp": ("Distribuidora Chopp Gelado", "11.222.333/0001-81"),
    "vinhos": ("Adega Bons Vinhos", None),
    "hortifruti": ("Hortifruti Fresco", None),
    "carnes": ("Frigorífico Boi Bom", None),
    "peixes": ("Peixaria Mar Aberto", None),
    "paes": ("Panificadora Trigo Bom", None),
    "gelo": ("Gelo Polar", None),
    "embalagens": ("Embalagens Leva e Traz", None),
    "limpeza": ("Limpeza Total Distribuidora", None),
    "gas": ("Gás Rápido", None),
    "banda": ("Banda Som da Praça", None),
    "contador": ("Contabilidade Exemplo", None),
}


def _dinheiro(valor: float) -> Decimal:
    return Decimal(str(round(valor, 2)))


def _dias_do_mes(ano: int, mes: int, ate: date) -> list[date]:
    dia = date(ano, mes, 1)
    dias = []
    while dia.month == mes and dia <= ate:
        dias.append(dia)
        dia += timedelta(days=1)
    return dias


def popular(db: Session, hoje: date, nome_restaurante: str, com_documentos: bool = True) -> dict[str, int]:
    """Cria usuário, restaurante e lançamentos fictícios. Devolve contagens para conferência."""
    sorteio = random.Random(2026)  # sempre os mesmos dados para a mesma data

    usuario = auth_service.registrar_usuario(db, "Demonstração", EMAIL, SENHA)
    restaurante = restaurante_service.criar(db, usuario, nome_restaurante, None).restaurante
    rid = restaurante.id

    categoria_service.criar(db, rid, "Música ao vivo e eventos")
    categorias = {c.nome: c.id for c in categoria_service.listar(db, rid, incluir_inativas=False)}
    fornecedores = {
        chave: fornecedor_service.criar(db, rid, FornecedorCreate(nome=nome, documento=documento)).id
        for chave, (nome, documento) in FORNECEDORES.items()
    }

    def despesa(dia: date, descricao: str, valor: float, categoria: str | None, fornecedor: str | None, nf=None):
        despesa_service.criar(
            db,
            rid,
            usuario.id,
            DespesaCreate(
                descricao=descricao,
                valor=_dinheiro(valor),
                data=dia,
                categoria_id=categorias[categoria] if categoria else None,
                fornecedor_id=fornecedores[fornecedor] if fornecedor else None,
                numero_documento=nf,
            ),
        )

    def conta(vencimento: date, descricao: str, valor: float, categoria: str, fornecedor: str | None = None):
        return conta_pagar_service.criar(
            db,
            rid,
            usuario.id,
            ContaPagarCreate(
                descricao=descricao,
                valor=_dinheiro(valor),
                data_vencimento=vencimento,
                categoria_id=categorias[categoria],
                fornecedor_id=fornecedores[fornecedor] if fornecedor else None,
            ),
        )

    indice_atual = hoje.year * 12 + hoje.month - 1
    for indice in range(indice_atual - MESES_DE_HISTORICO + 1, indice_atual + 1):
        ano, mes = divmod(indice, 12)
        mes += 1
        mes_atual = indice == indice_atual
        # Dezembro é mais movimentado (festas de fim de ano).
        movimento = 1.3 if mes == 12 else 1.0

        # --- compras do dia a dia (despesas) ---
        for dia in _dias_do_mes(ano, mes, hoje):
            semana = dia.weekday()  # 0 = segunda
            if semana == 1:  # terça: chopp, carnes, peixes, gelo
                despesa(dia, "Chopp pilsen - barris de 50 L", sorteio.uniform(1800, 2600) * movimento,
                        "Bebidas", "chopp", f"NF {sorteio.randint(7000, 9999)}")
                despesa(dia, "Carnes (picanha, alcatra, frango)", sorteio.uniform(2200, 3200) * movimento,
                        "Alimentos e insumos", "carnes")
                despesa(dia, "Peixes e camarão", sorteio.uniform(900, 1500) * movimento,
                        "Alimentos e insumos", "peixes")
                despesa(dia, "Gelo em cubos e em barra", sorteio.uniform(250, 380) * movimento, "Bebidas", "gelo")
            if semana in (1, 4):  # terça e sexta: hortifrúti e pães
                despesa(dia, "Hortifrúti: tomate, cebola, limão, verduras", sorteio.uniform(380, 650) * movimento,
                        "Alimentos e insumos", "hortifruti")
                despesa(dia, "Pães e massas", sorteio.uniform(120, 220), "Alimentos e insumos", "paes")
            if semana == 3 and dia.day <= 14:  # quinta, duas vezes por mês: vinhos e embalagens
                despesa(dia, "Vinhos e espumantes", sorteio.uniform(1200, 2000) * movimento, "Bebidas", "vinhos")
                despesa(dia, "Embalagens para delivery", sorteio.uniform(300, 500),
                        "Embalagens e descartáveis", "embalagens")
            if semana == 5:  # sábado: música ao vivo e gás
                despesa(dia, "Cachê da banda - música ao vivo no terraço", sorteio.uniform(800, 1200),
                        "Música ao vivo e eventos", "banda")
                if dia.day <= 7 or 15 <= dia.day <= 21:
                    despesa(dia, "Botijões de gás P45 (2 un.)", 1050, "Gás", "gas")

        primeiro_dia_util = date(ano, mes, 3)
        if primeiro_dia_util <= hoje:
            despesa(primeiro_dia_util, "Produtos de limpeza", sorteio.uniform(600, 900), "Limpeza e higiene", "limpeza")
            despesa(primeiro_dia_util, "Impulsionamento no Instagram", sorteio.uniform(300, 500), "Marketing", None)
        dia_manutencao = date(ano, mes, 18)
        if dia_manutencao <= hoje:
            reparo, valor = sorteio.choice([
                ("Manutenção do ar-condicionado", 450), ("Conserto da chopeira", 680),
                ("Troca de lâmpadas do terraço", 260), ("Manutenção da câmara fria", 1150),
            ])
            despesa(dia_manutencao, reparo, valor, "Manutenção", None)
            # Algumas compras sem categoria, para mostrar o filtro "Sem categoria" e a sugestão.
            despesa(dia_manutencao, "Compra no atacarejo", sorteio.uniform(150, 400), None, None)

        # --- contas mensais (vencimento) ---
        mensais = [
            (5, "Aluguel do imóvel", 6500, "Aluguel", None),
            (5, "Folha de pagamento", 18500 * (1.15 if mes == 12 else 1), "Folha de pagamento", None),
            (5, "Vale-transporte da equipe", 1200, "Folha de pagamento", None),
            (10, "Honorários contábeis", 900, "Serviços e assinaturas", "contador"),
            (12, "Conta de energia (Neoenergia)", sorteio.uniform(2300, 3100) * movimento, "Energia elétrica", None),
            (15, "Conta de água (Compesa)", sorteio.uniform(450, 600), "Água e esgoto", None),
            (20, "Internet e telefone", 199.90, "Serviços e assinaturas", None),
            (20, "DAS Simples Nacional", sorteio.uniform(3800, 4600) * movimento, "Impostos e taxas", None),
        ]
        for dia_vencimento, descricao, valor, categoria, fornecedor in mensais:
            vencimento = date(ano, mes, dia_vencimento)
            nova = conta(vencimento, descricao, valor, categoria, fornecedor)
            # Meses anteriores: tudo pago, no vencimento ou um pouco antes.
            # Mês atual: paga só o que venceu, EXCETO a energia (fica vencida para a demonstração).
            pagar = vencimento < hoje and not (mes_atual and "energia" in descricao)
            if not mes_atual or pagar:
                if vencimento <= hoje:
                    pagamento = vencimento - timedelta(days=sorteio.choice([0, 0, 1, 2]))
                    conta_pagar_service.pagar(db, nova, usuario.id, pagamento)

    # Contas extras para os alertas, qualquer que seja o dia: uma vencida, uma vencendo hoje e outras a vencer.
    conta(hoje - timedelta(days=2), "Boleto Hortifruti Fresco", 1340, "Alimentos e insumos", "hortifruti")
    conta(hoje, "Boleto Distribuidora Chopp Gelado", 2380, "Bebidas", "chopp")
    conta(hoje + timedelta(days=3), "Manutenção preventiva da câmara fria", 1150, "Manutenção")
    conta(hoje + timedelta(days=6), "Cachê - show especial de sexta", 1500, "Música ao vivo e eventos", "banda")

    documentos = 0
    if com_documentos:
        documentos = _documentos(db, restaurante, usuario, hoje)

    return {
        "restaurante_id": rid,
        "despesas": despesa_service.listar(db, rid, despesa_service.FiltroDespesas(), 1, 0)[1],
        "contas": conta_pagar_service.listar(
            db, rid, conta_pagar_service.FiltroContas(conta_pagar_service.FiltroSituacao.TODAS), 1, 0
        )[1],
        "documentos": documentos,
    }


def _documentos(db: Session, restaurante, usuario: Usuario, hoje: date) -> int:
    """Documentos esperando conferência: uma NF-e em PDF, uma foto da MESMA nota (duplicado) e um boleto."""
    ontem = (hoje - timedelta(days=1)).strftime("%d/%m/%Y")
    vencimento = (hoje + timedelta(days=4)).strftime("%d/%m/%Y")
    chave = "35261011222333000181550010000045211000000123"
    nota = [
        "DANFE - DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRONICA",
        "DISTRIBUIDORA CHOPP GELADO LTDA",
        "CNPJ 11.222.333/0001-81",
        "NOTA FISCAL N 4521",
        f"DATA DE EMISSAO {ontem}",
        f"CHAVE DE ACESSO {chave}",
        "CHOPP PILSEN BARRIL 50 L - 4 UN",
        "VALOR TOTAL DA NOTA R$ 2.140,00",
    ]
    arquivos = [
        ("nfe-distribuidora-chopp.pdf", pdf_com_texto(nota)),
        ("foto-da-nota-chopp.png", png_com_texto(nota[1:])),
        ("boleto-gas.png", png_com_texto([
            "GAS RAPIDO LTDA", "Beneficiario: Gas Rapido", f"Vencimento {vencimento}",
            "Valor do documento R$ 1.050,00", "Linha digitavel 23790.12345 60000.000003 00000.000000 1 99990000105000",
        ])),
    ]
    for nome, conteudo in arquivos:
        documento_service.enviar(db, restaurante, usuario.id, nome, conteudo)
    return len(arquivos)


def _limpar(db: Session) -> None:
    for tabela in reversed(Base.metadata.sorted_tables):
        db.execute(tabela.delete())
    db.commit()
    pasta = get_settings().documentos_dir
    if pasta.exists():
        shutil.rmtree(pasta)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria a demonstração com dados fictícios.")
    parser.add_argument("--nome", required=True, help="Nome do restaurante exibido na demonstração")
    parser.add_argument("--sem-documentos", action="store_true", help="Não envia os documentos de exemplo")
    argumentos = parser.parse_args()

    banco = make_url(get_settings().database_url).database or ""
    pasta = get_settings().documentos_dir
    # Travas de segurança: este script apaga tudo do banco e da pasta de documentos.
    if not banco.endswith("_demo"):
        print(f"Recusado: o banco '{banco}' não termina em '_demo'.", file=sys.stderr)
        return 1
    if "demonstracao" not in pasta.name:
        print(f"Recusado: a pasta de documentos '{pasta}' não é a da demonstração.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        _limpar(db)
        resumo = popular(db, date.today(), argumentos.nome.strip(), not argumentos.sem_documentos)
    engine.dispose()

    print(f"Demonstração criada: {resumo['despesas']} despesas, {resumo['contas']} contas, "
          f"{resumo['documentos']} documentos para conferir.")
    print(f"Login: {EMAIL}  |  Senha: {SENHA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
