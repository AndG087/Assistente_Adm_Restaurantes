"""Erros de regra de negócio, traduzidos em respostas HTTP pelas rotas."""


class RegistroDuplicadoError(Exception):
    """Violaria uma restrição de unicidade (ex.: CPF/CNPJ ou nome repetido)."""


class ReferenciaInvalidaError(Exception):
    """Um id informado não existe neste restaurante ou não pode ser usado."""


class OperacaoNaoPermitidaError(Exception):
    """O registro está em um estado que não permite a operação (ex.: alterar conta já paga)."""
