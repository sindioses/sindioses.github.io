import pytest
from keyring.backends.null import Keyring

from fb_posts_lib.credentials import read_token, require_native, save_token
from fb_posts_lib.models import CollectionError
from tests.fb_posts_doubles import MemorySecrets, UnavailableSecrets


@pytest.mark.boundary
def test_read_failure_is_safe() -> None:
    with pytest.raises(CollectionError) as caught:
        read_token(UnavailableSecrets(), "123")
    assert str(caught.value) == "No se pudo leer la credencial del keyring."


@pytest.mark.boundary
def test_save_failure_is_safe() -> None:
    with pytest.raises(CollectionError) as caught:
        save_token(UnavailableSecrets(), "123", "SECRET")
    assert str(caught.value) == "No se pudo guardar la credencial en el keyring."


@pytest.mark.boundary
def test_insecure_backend_rejected() -> None:
    with pytest.raises(CollectionError):
        require_native(Keyring())


@pytest.mark.boundary
def test_registration_and_replacement() -> None:
    store = MemorySecrets()
    save_token(store, "123", "first")
    save_token(store, "123", "second")
    assert read_token(store, "123") == "second"
    assert store.values == {("sindioses.fb-collect", "123"): "second"}


@pytest.mark.boundary
def test_missing_credential() -> None:
    with pytest.raises(CollectionError):
        read_token(MemorySecrets(), "123")


@pytest.mark.boundary
def test_empty_token_not_saved() -> None:
    store = MemorySecrets()
    with pytest.raises(CollectionError):
        save_token(store, "123", " ")
    assert store.values == {}
