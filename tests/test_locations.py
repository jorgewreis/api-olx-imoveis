from olx_imoveis.locations import ESTADOS, load_neighborhoods, load_regions


def test_estados_has_sp():
    assert "sp" in ESTADOS


def test_load_regions_sp():
    regions = load_regions("sp")
    assert len(regions) >= 1
    assert any(r["slug"] == "sao-paulo-e-regiao" for r in regions)


def test_load_neighborhoods_sp():
    bairros = load_neighborhoods("sp", "sao-paulo-e-regiao")
    assert any(b["slug"] == "centro" for b in bairros)


def test_load_regions_ba_ilheus():
    regions = load_regions("ba")
    ilheus = next(r for r in regions if r["nome"] == "Ilhéus")
    assert ilheus["slug"] == "sul-da-bahia/ilheus"
