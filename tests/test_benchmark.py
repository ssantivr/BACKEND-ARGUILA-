from app import benchmark


def test_every_case_measures_a_positive_time(monkeypatch):
    monkeypatch.setattr(benchmark, "ROUNDS", 1)
    monkeypatch.setattr(benchmark, "REPEATS", 5)

    for structure, operation, expected, measure in benchmark.CASES:
        assert structure and operation and expected.startswith("O(")
        assert measure(64) > 0


def test_report_is_a_markdown_table_with_one_row_per_case(monkeypatch, capsys):
    monkeypatch.setattr(benchmark, "ROUNDS", 1)
    monkeypatch.setattr(benchmark, "REPEATS", 5)
    monkeypatch.setattr(benchmark, "SIZES", (16, 32))

    benchmark.main()

    lines = capsys.readouterr().out.strip().splitlines()

    assert lines[0].startswith("| Estructura | Operación | Esperado | n = 16 | n = 32 | Crece |")
    assert len(lines) == len(benchmark.CASES) + 2
    assert all(line.startswith("| ") and line.endswith(" |") for line in lines[2:])


def test_times_keep_two_or_three_significant_digits():
    assert benchmark.format_time(0.2534) == "0.25"
    assert benchmark.format_time(44.84) == "44.8"
    assert benchmark.format_time(4349.2) == "4349"
