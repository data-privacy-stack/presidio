import sys

import pytest


def test_given_torch_is_missing_then_import_error_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)
    from presidio_image_redactor import EgoBlurRecognizer

    with pytest.raises(ImportError) as error:
        EgoBlurRecognizer(face_model_path="unused.jit")

    assert "presidio-image-redactor[egoblur]" in str(error.value)
