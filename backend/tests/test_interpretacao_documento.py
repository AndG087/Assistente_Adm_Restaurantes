import pytest

from app.services.interpretacao_documento import interpretar

# Chave de acesso de uma NF-e fictícia: UF 35, 10/2026, CNPJ 11.222.333/0001-81, modelo 55, série 1, nº 4521.
CHAVE = "3526101122233300018155001000004521100000012"
CHAVE_44 = CHAVE + "3"


def test_danfe_com_chave_de_acesso():
    texto = f"""
    DANFE
    DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA
    CHAVE DE ACESSO
    {' '.join(CHAVE_44[i:i + 4] for i in range(0, 44, 4))}
    DATA DA EMISSÃO
    05/10/2026
    DESTINATÁRIO CNPJ 11.444.777/0001-61
    VALOR TOTAL DOS PRODUTOS 1.100,00
    VALOR TOTAL DA NOTA
    1.234,56
    """

    dados = interpretar(texto, cnpj_do_restaurante="11444777000161")

    assert dados["chave_acesso"] == CHAVE_44
    assert dados["cnpj_emitente"] == "11222333000181"
    assert dados["numero_documento"] == "4521"
    assert dados["valor"] == "1234.56"
    assert dados["data_emissao"] == "2026-10-05"
    assert dados["tipo_sugerido"] == "despesa"


def test_boleto_vira_conta_a_pagar():
    texto = """
    Beneficiário: GÁS EXPRESS LTDA  CNPJ 11.222.333/0001-81
    Vencimento 25/10/2026
    Valor do Documento R$ 380,00
    Linha digitável 23790.12345 60000.000003 00000.000000 1 99990000038000
    """

    dados = interpretar(texto)

    assert dados["tipo_sugerido"] == "conta"
    assert dados["data_vencimento"] == "2026-10-25"
    assert dados["valor"] == "380.00"
    assert dados["cnpj_emitente"] == "11222333000181"


def test_cupom_sem_rotulo_usa_o_maior_valor():
    texto = "Pão francês 12,50\nLeite 8,90\nQueijo 45,00\n12/10/2026"

    dados = interpretar(texto)

    assert dados["valor"] == "45.00"
    assert dados["data_emissao"] == "2026-10-12"


def test_ignora_o_cnpj_do_proprio_restaurante_e_cnpjs_invalidos():
    texto = "Pagador CNPJ 11.444.777/0001-61\nCNPJ 11.222.333/0001-82\nEmitente 11.222.333/0001-81"

    assert interpretar(texto, cnpj_do_restaurante="11444777000161")["cnpj_emitente"] == "11222333000181"


@pytest.mark.parametrize(
    "linha",
    ["NOTA FISCAL N 004521", "Nota Fiscal Nº 4521", "NF-e nº: 4.521", "Número do documento: 4521", "N° 004521"],
)
def test_formatos_do_numero_do_documento(linha):
    assert interpretar(f"{linha}\nTotal 10,00")["numero_documento"] == "4521"


def test_ignora_datas_impossiveis_e_texto_sem_dados():
    dados = interpretar("Data 31/02/2026\nsem valores aqui")

    assert dados["data_emissao"] is None
    assert dados["valor"] is None
    assert dados["cnpj_emitente"] is None
