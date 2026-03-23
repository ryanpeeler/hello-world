"""Tests for hardware detection."""

from researchclaw.hardware import HardwareProfile, detect_hardware, is_metric_name


def test_detect_hardware_returns_profile():
    """detect_hardware should return a HardwareProfile."""
    hw = detect_hardware()
    assert isinstance(hw, HardwareProfile)
    assert hw.gpu_type in ("cuda", "mps", "cpu")
    assert hw.tier in ("high", "limited", "cpu_only")


def test_hardware_profile_to_dict():
    """HardwareProfile should be serializable."""
    hw = HardwareProfile(
        has_gpu=False, gpu_type="cpu", gpu_name="CPU only",
        vram_mb=None, tier="cpu_only", warning="No GPU",
    )
    d = hw.to_dict()
    assert d["gpu_type"] == "cpu"
    assert d["has_gpu"] is False


def test_is_metric_name():
    """Metric names should pass, log words should fail."""
    assert is_metric_name("accuracy")
    assert is_metric_name("f1_score")
    assert is_metric_name("loss")
    assert not is_metric_name("running epoch 1")
    assert not is_metric_name("loading model from checkpoint path that is very long and has many words")
