from logwise.parsing.normalizers import normalize_response_time, normalize_status


def test_response_time_units():
    assert normalize_response_time("142ms") == 142.0
    assert normalize_response_time("0.142s") == 142.0
    assert normalize_response_time("142") == 142.0          # bare -> ms
    assert normalize_response_time("-") is None
    assert normalize_response_time("") is None
    assert normalize_response_time("abc") is None


def test_status():
    assert normalize_status("200") == 200
    assert normalize_status("-") is None
    assert normalize_status("") is None
    assert normalize_status("999") is None                  # implausible -> None
    assert normalize_status("notanumber") is None
