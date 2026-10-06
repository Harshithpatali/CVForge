from app.services.github_inspector import _repo_full_name, _technology_hints


def test_github_repo_url_normalization():
    assert _repo_full_name("https://github.com/owner/project") == "owner/project"
    assert _repo_full_name("github.com/owner/project") == "owner/project"
    assert _repo_full_name("owner/project") == "owner/project"


def test_repository_technology_hints():
    technologies = _technology_hints(
        [
            "requirements.txt",
            "Dockerfile",
            "src/model.py",
            "app.py",
        ],
        {"Python": 9000},
        "Built with FastAPI and Streamlit using XGBoost.",
    )

    assert "Python" in technologies
    assert "Docker" in technologies
    assert "FastAPI" in technologies
    assert "Streamlit" in technologies
    assert "XGBoost" in technologies
