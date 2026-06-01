"""Testes de ordenação de imóveis."""

from olx_imoveis.listing_display import sort_imoveis
from olx_imoveis.models import ImovelResumo, SearchFilters, TipoOferta


def _item(
    list_id: str,
    *,
    estado: str = "BA",
    cidade: str = "Ilhéus",
    bairro: str = "Centro",
    preco: int = 100_000,
    tipo_oferta: TipoOferta | None = TipoOferta.VENDA,
) -> ImovelResumo:
    return ImovelResumo(
        list_id=list_id,
        titulo=f"Imóvel {list_id}",
        url=f"https://www.olx.com.br/vi/{list_id}.htm",
        estado=estado,
        cidade=cidade,
        bairro=bairro,
        preco=preco,
        tipo_oferta=tipo_oferta,
    )


def test_sort_by_location_then_tipo_then_price():
    items = [
        _item("4", bairro="Pontal", preco=500_000, tipo_oferta=TipoOferta.VENDA),
        _item("1", bairro="Centro", preco=300_000, tipo_oferta=TipoOferta.ALUGUEL),
        _item("2", bairro="Centro", preco=200_000, tipo_oferta=TipoOferta.VENDA),
        _item("3", bairro="Centro", preco=150_000, tipo_oferta=TipoOferta.VENDA),
        _item("5", estado="SP", cidade="São Paulo", bairro="Centro", preco=100_000),
    ]
    ordered = sort_imoveis(items)
    assert [i.list_id for i in ordered] == ["1", "3", "2", "4", "5"]


def test_sort_aluguel_before_venda_same_location():
    items = [
        _item("v", preco=400_000, tipo_oferta=TipoOferta.VENDA),
        _item("a", preco=2_000, tipo_oferta=TipoOferta.ALUGUEL),
    ]
    ordered = sort_imoveis(items)
    assert ordered[0].list_id == "a"
    assert ordered[1].list_id == "v"
