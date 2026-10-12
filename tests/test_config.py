from sanad.config import load_settings


def test_settings_have_models():
    s = load_settings()
    assert s["ollama"]["chat_model"]
    assert s["ollama"]["embed_model"]
