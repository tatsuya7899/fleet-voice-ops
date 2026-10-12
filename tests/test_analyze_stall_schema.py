"""SPEC-initial.md §agenticの実体 / §プライバシー境界 受入条件②:
analyze_stall出力のキー集合が固定スキーマと完全一致し、
evidence_signals[]の各要素が第1層許可キーのいずれかであること。
"""
from __future__ import annotations

from fleet_voice_ops.app.tools import analyze_stall
from fleet_voice_ops.lib.emit import LAYER2_HYPOTHESIS_KEYS, LAYER2_TOP_KEYS, is_allowed_layer1_key


def test_analyze_stall_top_level_schema_matches_exactly():
    result = analyze_stall("demo-birch")
    assert set(result.keys()) == LAYER2_TOP_KEYS


def test_analyze_stall_hypothesis_schema_and_evidence_signals():
    result = analyze_stall("demo-birch")
    hypotheses = result["hypotheses"]
    assert 2 <= len(hypotheses) <= 3, "SPECは複数(2〜3個)の仮説を要求する"
    for hyp in hypotheses:
        assert set(hyp.keys()) == LAYER2_HYPOTHESIS_KEYS
        assert hyp["confidence"] in {"low", "medium", "high"}
        assert hyp["evidence_signals"], "evidence_signalsは空であってはならない"
        for signal_key in hyp["evidence_signals"]:
            assert is_allowed_layer1_key(signal_key), (
                f"evidence_signalsは第1層許可キーの名のみを含むこと: {signal_key}"
            )


def test_analyze_stall_recommended_action_is_nonempty_string():
    result = analyze_stall("demo-birch")
    assert isinstance(result["recommended_action"], str)
    assert result["recommended_action"]


def test_analyze_stall_unknown_session_raises():
    import pytest

    with pytest.raises(ValueError):
        analyze_stall("session-that-does-not-exist")
