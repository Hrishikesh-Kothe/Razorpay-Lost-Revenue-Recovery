from app.engine.graph import recovery_graph


def test_graph_exists():
    assert recovery_graph is not None