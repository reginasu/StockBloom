import os


def test_missing_streamlit_secrets_falls_back_to_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    import yf_3_web_0917_1

    assert yf_3_web_0917_1.get_app_secret("SUPABASE_URL") == "https://example.supabase.co"
    assert yf_3_web_0917_1.get_app_secret("SUPABASE_KEY") == "test-key"
