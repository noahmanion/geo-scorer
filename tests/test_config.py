from geo import config


def test_expand_cells_substitutes_city_and_state():
    cities = [{"name": "Chicago", "state": "IL"}]
    queries = [{"id": "disc_001", "segment": "discovery",
                "template": "Who offers at-home Botox in {city}?"}]
    cells = config.expand_cells(cities, queries)
    assert len(cells) == 1
    cell = cells[0]
    assert cell["city"] == "Chicago"
    assert cell["state"] == "IL"
    assert cell["query_id"] == "disc_001"
    assert cell["segment"] == "discovery"
    assert cell["prompt"] == "Who offers at-home Botox in Chicago, IL?"


def test_expand_cells_is_full_cross_product():
    cities = [{"name": "Chicago", "state": "IL"},
              {"name": "Denver", "state": "CO"}]
    queries = [{"id": "a", "segment": "s", "template": "x {city}"},
               {"id": "b", "segment": "s", "template": "y {city}"}]
    assert len(config.expand_cells(cities, queries)) == 4


def test_real_config_files_load_and_expand():
    cities = config.load_cities()
    queries = config.load_queries()
    brand = config.load_brand()
    assert brand["name"] == "Pinch"
    assert "bookpinch" in brand["aliases"]
    cells = config.expand_cells(cities, queries)
    assert len(cells) == len(cities) * len(queries)
    assert all("{city}" not in c["prompt"] for c in cells)
