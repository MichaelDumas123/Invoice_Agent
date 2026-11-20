from invoice_assistant.observability.metrics import Metrics


def test_metrics_allow_only_safe_labels_and_aggregate_counts():
    metrics = Metrics()
    metrics.increment("http_requests_total", {"route": "drafts", "status": "200", "invoice_number": "secret-123"})
    snapshot = metrics.snapshot()
    assert snapshot == [{"name": "http_requests_total", "labels": {"route": "drafts", "status": "200"}, "value": 1}]
