from evaluate_system_layers import RETRIEVAL_CASES, ROUTING_CASES, evaluate_retrieval


def test_retrieval_benchmark_covers_every_topic_in_both_languages():
    expected = {topic for _, topic, _ in RETRIEVAL_CASES}
    assert len(expected) == 14
    for language in ("en", "rw"):
        rows = [row for row in RETRIEVAL_CASES if row[0] == language]
        assert len(rows) == 14
        assert {row[1] for row in rows} == expected
        assert len({row[2] for row in rows}) == 14


def test_routing_benchmark_covers_required_categories_and_languages():
    assert {row[0] for row in ROUTING_CASES} == {
        "crisis", "referral", "greeting", "offtopic", "wellbeing",
    }
    assert {row[1] for row in ROUTING_CASES} == {"en", "rw"}


class PerfectRetriever:
    def retrieve(self, query, k, lang):
        expected = next(topic for language, topic, text in RETRIEVAL_CASES if text == query and language == lang)
        distractors = [topic for _, topic, _ in RETRIEVAL_CASES if topic != expected][:2]
        return [({"id": topic}, 1.0 / rank) for rank, topic in enumerate([expected, *distractors], start=1)]


def test_retrieval_metric_calculation_for_perfect_router():
    metrics, rows = evaluate_retrieval(PerfectRetriever())
    assert len(rows) == 28
    assert metrics["overall_top_1_accuracy"] == 1.0
    assert metrics["overall_top_3_recall"] == 1.0
