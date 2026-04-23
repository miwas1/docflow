from classifier_service.config import ClassifierSettings


def build_settings(**overrides) -> ClassifierSettings:
    payload = {
        "POSTGRES_DSN": "postgresql+psycopg://doc_platform:doc_platform@localhost:5432/doc_platform",
        "RABBITMQ_URL": "amqp://doc_platform:doc_platform@localhost:5672/doc_platform",
        "OBJECT_STORAGE_ENDPOINT": "http://localhost:9000",
        "OBJECT_STORAGE_BUCKET": "doc-platform-artifacts",
        "OBJECT_STORAGE_ACCESS_KEY": "minioadmin",
        "OBJECT_STORAGE_SECRET_KEY": "minioadmin",
        "CLASSIFIER_MODEL_NAME": "/models/finetuned/current",
        "CLASSIFIER_MODEL_VERSION": "modernbert-finetuned-local",
        "CLASSIFIER_MODEL_PROVIDER": "huggingface",
        "CLASSIFIER_MODEL_CACHE_DIR": "/models/huggingface",
        "CLASSIFIER_DEVICE": "cpu",
    }
    payload.update(overrides)
    return ClassifierSettings(**payload)


def test_classifier_settings_parse_label_descriptions_and_cache_defaults() -> None:
    settings = build_settings()

    assert settings.classifier_model_name == "/models/finetuned/current"
    assert settings.classifier_model_provider == "huggingface"
    assert settings.classifier_model_cache_dir == "/models/huggingface"
    assert settings.classifier_device == "cpu"
    assert isinstance(settings.classifier_label_descriptions, dict)


def test_classifier_settings_accept_json_string_label_descriptions() -> None:
    settings = build_settings(
        CLASSIFIER_LABEL_DESCRIPTIONS_JSON='{"invoice":"Invoice form","unknown_other":"Unknown"}'
    )

    assert settings.classifier_label_descriptions == {
        "invoice": "Invoice form",
        "unknown_other": "Unknown",
    }
