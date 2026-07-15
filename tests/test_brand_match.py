from geo import config


def test_domain_cited_matches_host_ignoring_www_and_path():
    cites = ["https://www.bookpinch.com/chicago", "https://yelp.com/biz/x"]
    assert config.brand_domain_cited("bookpinch.com", cites) is True


def test_domain_cited_false_when_absent():
    cites = ["https://yelp.com/biz/x", "https://groupon.com/y"]
    assert config.brand_domain_cited("bookpinch.com", cites) is False


def test_domain_cited_handles_pinchmed_redirect_domain():
    cites = ["http://pinchmed.com/"]
    assert config.brand_domain_cited("pinchmed.com", cites) is True


def test_domain_cited_empty_list():
    assert config.brand_domain_cited("bookpinch.com", []) is False
