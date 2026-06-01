"""Modelos de domínio."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TipoOferta(str, Enum):
    VENDA = "venda"
    ALUGUEL = "aluguel"


OLX_CATEGORY_VENDA = 1001
OLX_CATEGORY_ALUGUEL = 1002

MIN_VENDA_PRECO = 100_000
MAX_ALUGUEL_PRECO = 20_000


class TipoImovel(str, Enum):
    APARTAMENTOS = "apartamentos"
    CASAS = "casas"
    TERRENOS = "terrenos"
    COMERCIO = "comercio-e-industria"
    TEMPORADA = "temporada"
    QUARTOS = "quartos"


class TipoAnunciante(str, Enum):
    COMUM = "comum"
    PROFISSIONAL = "profissional"


class SearchFilters(BaseModel):
    estado: str = Field(description="Sigla UF, ex: sp")
    regiao: str = Field(default="estado-sp", description="Slug da região/cidade")
    bairro: str | None = Field(default=None, description="Slug do bairro opcional")
    tipo_imovel: TipoImovel | None = TipoImovel.APARTAMENTOS
    tipo_oferta: TipoOferta | None = TipoOferta.VENDA
    tipo_anunciante: TipoAnunciante | None = None
    preco_min: int | None = None
    preco_max: int | None = None
    quartos_min: int | None = None
    quartos_max: int | None = None
    banheiros_min: int | None = None
    vagas_min: int | None = None
    termo: str | None = None
    pagina: int = 1


class Anunciante(BaseModel):
    nome: str | None = None
    public_account_id: str | None = None
    is_professional: bool = False
    profile_url: str | None = None


class ImovelResumo(BaseModel):
    list_id: str
    titulo: str
    preco: int | None = None
    preco_label: str | None = None
    url: str
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    imagem_url: str | None = None
    quartos: int | None = None
    area_m2: int | None = None


class ImovelDetalhe(ImovelResumo):
    descricao: str | None = None
    imagens: list[str] = Field(default_factory=list)
    atributos: dict[str, Any] = Field(default_factory=dict)
    anunciante: Anunciante = Field(default_factory=Anunciante)
    telefone: str | None = None
    telefone_mascarado: bool = False


class SearchResult(BaseModel):
    items: list[ImovelResumo]
    total: int | None = None
    pagina: int = 1
    tem_mais: bool = False
    url_busca: str | None = None
