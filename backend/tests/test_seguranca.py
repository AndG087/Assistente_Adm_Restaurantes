from app.core.seguranca import gerar_hash_senha, gerar_token_sessao, hash_token, verificar_senha


def test_hash_de_senha_confere_apenas_com_a_senha_correta():
    hash_ = gerar_hash_senha("minha-senha-123")

    assert verificar_senha("minha-senha-123", hash_)
    assert not verificar_senha("minha-senha-124", hash_)
    assert "minha-senha-123" not in hash_


def test_mesma_senha_gera_hashes_diferentes():
    assert gerar_hash_senha("igual") != gerar_hash_senha("igual")


def test_hash_corrompido_ou_de_outro_algoritmo_nao_quebra():
    assert not verificar_senha("x", "")
    assert not verificar_senha("x", "texto-qualquer")
    assert not verificar_senha("x", "bcrypt$1$2$3$abc$def")
    assert not verificar_senha("x", "scrypt$nao-numero$8$1$abc$def")


def test_token_de_sessao_e_aleatorio_e_hash_e_deterministico():
    token = gerar_token_sessao()

    assert token != gerar_token_sessao()
    assert len(token) >= 40
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64
