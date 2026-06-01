from olx_imoveis.models import SearchFilters, TipoImovel, TipoOferta
from olx_imoveis.url_builder import build_search_url


def test_build_basic_url():
    f = SearchFilters(estado="sp", regiao="sao-paulo-e-regiao")
    url = build_search_url(f)
    assert (
        url
        == "https://www.olx.com.br/imoveis/venda/apartamentos/estado-sp/sao-paulo-e-regiao?ps=100000"
    )


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
    assert "www.olx.com.br" in url
    assert "estado-rj" in url
    assert "zona-sul" in url
    assert "aluguel" in url
    assert "casas" in url
    assert "ps=1000" in url
    assert "pe=5000" in url
    assert "se=2" in url
    assert "page=2" in url


def test_build_todos_oferta_url():
    f = SearchFilters(
        estado="ba",
        regiao="sul-da-bahia/ilheus",
        tipo_oferta=None,
        tipo_imovel=TipoImovel.APARTAMENTOS,
    )
    url = build_search_url(f)
    assert url == "https://www.olx.com.br/imoveis/apartamentos/estado-ba/sul-da-bahia/ilheus"


def test_build_todos_tipo_url():
    f = SearchFilters(
        estado="ba",
        regiao="sul-da-bahia/ilheus",
        tipo_oferta=TipoOferta.VENDA,
        tipo_imovel=None,
    )
    url = build_search_url(f)
    assert url == "https://www.olx.com.br/imoveis/venda/estado-ba/sul-da-bahia/ilheus?ps=100000"


def test_build_city_with_macro_region():
    f = SearchFilters(
        estado="ba",
        regiao="sul-da-bahia/ilheus",
        bairro="centro",
    )
    url = build_search_url(f)
    assert (
        url
        == "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ba/sul-da-bahia/ilheus/centro?ps=100000"
    )
