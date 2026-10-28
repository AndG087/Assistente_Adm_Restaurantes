"""Classificação por palavras-chave do vocabulário de restaurantes (determinística, sem IA).

As regras usam os nomes das categorias padrão; se o restaurante renomear ou inativar
uma categoria, a regra correspondente simplesmente deixa de valer.
A ordem importa: regras mais específicas vêm antes ("água sanitária" é limpeza, não conta de água).
"""

import re
import unicodedata
from dataclasses import dataclass

_REGRAS: list[tuple[str, list[str]]] = [
    ("Limpeza e higiene", [
        r"detergente", r"sabao", r"desinfetante", r"agua sanitaria", r"alvejante", r"esponja", r"papel higienico",
        r"papel toalha", r"alcool (em )?gel", r"alcool 70", r"saco(s)? de lixo", r"limpeza", r"higiene",
        r"multiuso", r"\bcloro\b", r"luva(s)? (descartave|de latex|nitrilica)",
    ]),
    ("Embalagens e descartáveis", [
        r"descartave", r"embalage", r"marmit", r"quentinha", r"sacola", r"guardanapo", r"canudo",
        r"filme pvc", r"papel aluminio", r"isopor", r"caixa(s)? (de|para) pizza", r"\bpotes? (plastic|descart)",
    ]),
    ("Bebidas", [
        r"refrigerante", r"\bcoca\b", r"guarana", r"\bpepsi\b", r"\bfanta\b", r"cerveja", r"chop+", r"\bvinhos?\b",
        r"\bsucos?\b", r"agua mineral", r"agua com gas", r"energetico", r"whisky", r"vodka", r"cachaca",
        r"long neck", r"bebida",
    ]),
    ("Gás", [r"\bgas\b", r"botijao", r"\bglp\b", r"ultragaz", r"liquigas", r"supergasbras", r"copagaz"]),
    ("Energia elétrica", [
        r"energia", r"\bluz\b", r"eletricidade", r"\benel\b", r"cemig", r"copel", r"\blight\b", r"\bcpfl\b",
        r"celesc", r"coelba", r"celpe", r"equatorial", r"neoenergia", r"elektro",
    ]),
    ("Água e esgoto", [
        r"\bagua\b", r"esgoto", r"sabesp", r"copasa", r"cedae", r"sanepar", r"embasa", r"compesa", r"caesb",
        r"saneamento",
    ]),
    ("Aluguel", [r"aluguel", r"condominio", r"locacao do (imovel|salao|ponto|predio)"]),
    ("Folha de pagamento", [
        r"salario", r"folha de pagamento", r"funcionari", r"\bferias\b", r"13o salario", r"decimo terceiro",
        r"rescisao", r"vale[- ]transporte", r"vale[- ]refeicao", r"\bfgts\b", r"\binss\b", r"pro[- ]labore",
        r"comissao", r"gorjeta", r"diarista", r"freelancer",
    ]),
    ("Impostos e taxas", [
        r"imposto", r"simples nacional", r"\bdas[- ]?(mei|simples)\b", r"guia (do )?das\b", r"\bicms\b",
        r"\biss\b", r"\biptu\b", r"alvara", r"\bdarf\b", r"tributo", r"vigilancia sanitaria",
        r"taxa (de licenca|municipal|do bombeiro|de funcionamento)",
    ]),
    ("Manutenção", [
        r"conserto", r"manutencao", r"reparo", r"assistencia tecnica", r"encanador", r"eletricista",
        r"dedetizacao", r"pintura", r"troca de (peca|oleo|lampada)",
    ]),
    # Categoria opcional (não está entre as padrão): vale para restaurantes que a criarem com este nome.
    ("Música ao vivo e eventos", [
        r"musica ao vivo", r"\bbanda\b", r"\bshows?\b", r"\bdj\b", r"\bmusicos?\b", r"cache (do|da|de)",
        r"voz e violao",
    ]),
    ("Marketing", [
        r"anuncio", r"propaganda", r"publicidade", r"marketing", r"instagram", r"facebook", r"google ads",
        r"panfleto", r"\bfolder\b", r"\bbanner\b", r"impulsionamento", r"influenciador",
    ]),
    ("Serviços e assinaturas", [
        r"assinatura", r"mensalidade", r"internet", r"telefone", r"celular", r"software", r"\bsistema\b",
        r"aplicativo", r"\bifood\b", r"\brappi\b", r"maquininha", r"contabil", r"contador", r"tarifa bancaria",
        r"\bseguro\b", r"streaming",
    ]),
    ("Alimentos e insumos", [
        r"\bcarnes?\b", r"frango", r"peixe", r"picanha", r"alcatra", r"\bfile\b", r"linguica", r"bacon",
        r"presunto", r"queijo", r"mussarela", r"calabresa", r"\bleite\b", r"manteiga", r"\bovos?\b", r"\barroz\b",
        r"feijao", r"farinha", r"\btrigo\b", r"acucar", r"\boleo\b", r"azeite", r"tomate", r"cebola", r"\balho\b",
        r"batata", r"verdura", r"legume", r"\bfrutas?\b", r"hortifruti", r"tempero", r"\bmolho", r"macarrao",
        r"\bmassas?\b", r"\bpao\b", r"\bpaes\b", r"insumo", r"hortalica",
    ]),
]

_COMPILADAS = [(categoria, [re.compile(p) for p in padroes]) for categoria, padroes in _REGRAS]


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, SEM mudar o tamanho do texto (cada caractere vira um), para os índices baterem."""
    return "".join(unicodedata.normalize("NFKD", c)[0] for c in texto.lower())


def chave_de_nome(nome: str) -> str:
    return normalizar(nome).strip()


@dataclass(frozen=True)
class Reconhecimento:
    categoria: str  # nome da categoria padrão
    trecho: str  # trecho do texto original que acionou a regra


def reconhecer(descricao: str, categorias_disponiveis: set[str]) -> Reconhecimento | None:
    """Primeira regra que casa com a descrição, entre as categorias disponíveis (nomes normalizados)."""
    texto = normalizar(descricao)
    for categoria, padroes in _COMPILADAS:
        if chave_de_nome(categoria) not in categorias_disponiveis:
            continue
        for padrao in padroes:
            achado = padrao.search(texto)
            if achado:
                return Reconhecimento(categoria, descricao[achado.start() : achado.end()])
    return None
