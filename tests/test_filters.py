from olx_imoveis.models import (
    MAX_ALUGUEL_PRECO,
    MIN_VENDA_PRECO,
    OLX_CATEGORY_ALUGUEL,
    OLX_CATEGORY_VENDA,
    SearchFilters,
    TipoAnunciante,
    TipoOferta,
)
from olx_imoveis.parsers.common import is_professional_ad, slugify_label
from olx_imoveis.parsers.listing import _matches_anunciante_tipo, _matches_bairro, _matches_offer_type, _matches_price_range
from olx_imoveis.url_builder import build_search_url, effective_price_range


def test_venda_and_aluguel_urls_differ():
    base = dict(estado="ba", regiao="sul-da-bahia/ilheus")
    venda = build_search_url(SearchFilters(**base, tipo_oferta=TipoOferta.VENDA))
    aluguel = build_search_url(SearchFilters(**base, tipo_oferta=TipoOferta.ALUGUEL))
    assert "/imoveis/venda/" in venda
    assert "/imoveis/aluguel/" in aluguel
    assert venda != aluguel


def test_price_and_quartos_query_params():
    f = SearchFilters(
        estado="ba",
        regiao="sul-da-bahia/ilheus",
        preco_min=200000,
        preco_max=500000,
        quartos_min=3,
        termo="piscina",
        pagina=2,
    )
    url = build_search_url(f)
    assert "ps=200000" in url
    assert "pe=500000" in url
    assert "se=3" in url
    assert "q=piscina" in url
    assert "page=2" in url


def test_matches_offer_type_filters_category():
    assert _matches_offer_type({"searchCategoryLevelOne": OLX_CATEGORY_VENDA}, TipoOferta.VENDA)
    assert not _matches_offer_type({"searchCategoryLevelOne": OLX_CATEGORY_VENDA}, TipoOferta.ALUGUEL)
    assert _matches_offer_type({"searchCategoryLevelOne": OLX_CATEGORY_ALUGUEL}, TipoOferta.ALUGUEL)
    assert _matches_offer_type({}, TipoOferta.VENDA)


def test_default_price_limits_in_url():
    venda = build_search_url(
        SearchFilters(estado="ba", regiao="sul-da-bahia/ilheus", tipo_oferta=TipoOferta.VENDA)
    )
    aluguel = build_search_url(
        SearchFilters(estado="ba", regiao="sul-da-bahia/ilheus", tipo_oferta=TipoOferta.ALUGUEL)
    )
    assert f"ps={MIN_VENDA_PRECO}" in venda
    assert f"pe={MAX_ALUGUEL_PRECO}" in aluguel


def test_price_limits_respect_user_stricter_values():
    pmin, pmax = effective_price_range(
        SearchFilters(estado="ba", tipo_oferta=TipoOferta.VENDA, preco_min=250_000)
    )
    assert pmin == 250_000

    pmin, pmax = effective_price_range(
        SearchFilters(estado="ba", tipo_oferta=TipoOferta.ALUGUEL, preco_max=5_000)
    )
    assert pmax == 5_000


def test_matches_price_range():
    assert _matches_price_range({"priceValue": 150_000}, TipoOferta.VENDA)
    assert not _matches_price_range({"priceValue": 50_000}, TipoOferta.VENDA)
    assert _matches_price_range({"priceValue": 1_500}, TipoOferta.ALUGUEL)
    assert not _matches_price_range({"priceValue": 25_000}, TipoOferta.ALUGUEL)
    assert _matches_price_range({}, TipoOferta.VENDA)
    assert _matches_price_range({"priceValue": 150_000, "searchCategoryLevelOne": 1001}, None)
    assert not _matches_price_range({"priceValue": 25_000, "searchCategoryLevelOne": 1002}, None)


def test_matches_bairro():
    ad = {"locationDetails": {"neighbourhood": "Centro", "municipality": "Ilhéus"}}
    assert _matches_bairro(ad, "centro")
    assert not _matches_bairro(ad, "pontal")
    assert slugify_label("São Francisco") == "sao-francisco"


def test_anunciante_url_and_filter():
    comum_url = build_search_url(
        SearchFilters(estado="ba", regiao="sul-da-bahia/ilheus", tipo_anunciante=TipoAnunciante.COMUM)
    )
    pro_url = build_search_url(
        SearchFilters(
            estado="ba",
            regiao="sul-da-bahia/ilheus",
            tipo_anunciante=TipoAnunciante.PROFISSIONAL,
        )
    )
    assert "f=0" in comum_url
    assert "f=1" in pro_url

    assert _matches_anunciante_tipo({"professionalAd": False}, TipoAnunciante.COMUM)
    assert not _matches_anunciante_tipo({"professionalAd": True}, TipoAnunciante.COMUM)
    assert _matches_anunciante_tipo({"professionalAd": True}, TipoAnunciante.PROFISSIONAL)
    assert not _matches_anunciante_tipo({"professionalAd": False}, TipoAnunciante.PROFISSIONAL)


def test_creci_in_description_counts_as_professional():
    ad = {"professionalAd": False, "body": "Corretor credenciado CRECI/BA 12345"}
    assert is_professional_ad(ad)
    assert _matches_anunciante_tipo(ad, TipoAnunciante.PROFISSIONAL)
    assert not _matches_anunciante_tipo(ad, TipoAnunciante.COMUM)

    ad_no_creci = {"professionalAd": False, "body": "Apartamento à venda, porteira fechada."}
    assert not is_professional_ad(ad_no_creci)
    assert _matches_anunciante_tipo(ad_no_creci, TipoAnunciante.COMUM)

    assert is_professional_ad({"professionalAd": False}, descricao="Entre em contato. CRECI 98765.")
