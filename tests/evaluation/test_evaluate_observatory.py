from scripts.evaluate_observatory import classification


def test_classification_reports_precision_recall_and_f1() -> None:
    result = classification({"a", "b", "c"}, {"b", "c", "d"})

    assert result == {
        "expected": 3,
        "observed": 3,
        "true_positive": 2,
        "false_positive": 1,
        "false_negative": 1,
        "precision": 0.6667,
        "recall": 0.6667,
        "f1": 0.6667,
    }
