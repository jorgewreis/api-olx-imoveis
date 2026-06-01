from olx_imoveis.models import SearchFilters, TipoImovel, TipoOferta
from olx_imoveis.url_builder import build_search_url


def test_build_basic_url():
    f = SearchFilters(estado="sp", regiao="sao-paulo-e-regiao")
    url = build_search_url(f)
    assert url == "https://sp.olx.com.br/sao-paulo-e-regiao/imoveis/venda/apartamentos"


def test_build_with_filters():
    f = SearchFilters(
        estado="rj",
        regiao="rio-de-janeiro-e-regiao",
        bairro="zona-sul",
        tipo_imovel=TipoImovel.CASAS,
        tipo_oferta=TipoOferta.ALUGUEL,
        preco_min=1000,
        preco_max=5000,
        quartos_min=2,
        pagina=2,
    )
    url = build_search_url(f)
    assert "rj.olx.com.br" in url
    assert "zona-sul" in url
    assert "aluguel" in url
    assert "casas" in url
    assert "ps=1000" in url
    assert "pe=5000" in url
    assert "se=2" in url
    assert "page=2" in url
