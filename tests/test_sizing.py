from arb_bot.engine.sizing import has_two_sided_edge

def test_edge():
    assert has_two_sided_edge(0.48, 0.50)
    assert not has_two_sided_edge(0.52, 0.49)
