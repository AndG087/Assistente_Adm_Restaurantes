import pytest

from app.schemas.validadores import (
    cnpj_valido,
    cpf_valido,
    normalizar_documento,
    normalizar_email,
    normalizar_telefone,
)


@pytest.mark.parametrize(
    ("cpf", "valido"),
    [
        ("52998224725", True),
        ("11144477735", True),
        ("52998224724", False),
        ("11111111111", False),
        ("5299822472", False),
    ],
)
def test_cpf(cpf, valido):
    assert cpf_valido(cpf) is valido


@pytest.mark.parametrize(
    ("cnpj", "valido"),
    [
        ("11222333000181", True),
        ("11444777000161", True),
        ("11222333000182", False),
        ("00000000000000", False),
        ("1122233300018", False),
    ],
)
def test_cnpj(cnpj, valido):
    assert cnpj_valido(cnpj) is valido


def test_documento_aceita_cpf_ou_cnpj_com_pontuacao():
    assert normalizar_documento("529.982.247-25") == "52998224725"
    assert normalizar_documento("11.222.333/0001-81") == "11222333000181"
    assert normalizar_documento("  ") is None
    with pytest.raises(ValueError):
        normalizar_documento("123.456.789-00")


def test_email_e_telefone():
    assert normalizar_email(" Compras@Fornecedor.com ") == "compras@fornecedor.com"
    assert normalizar_email("") is None
    with pytest.raises(ValueError):
        normalizar_email("sem-arroba")

    assert normalizar_telefone("(11)  98765-4321") == "(11) 98765-4321"
    with pytest.raises(ValueError):
        normalizar_telefone("telefone")
