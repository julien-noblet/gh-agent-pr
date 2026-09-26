import os
import tempfile
from pathlib import Path
import pytest
import yaml

from gh_agent_pr.config import load_config, Config


def test_default_config():
    config = load_config(config_path="/nonexistent/path/config.yaml")
    assert config.repos == []
    assert config.limit == 20
    assert config.laya_model == "english"


def test_cli_repos_override():
    config = load_config(cli_repos=["user/repo1", "user/repo2"], limit=10)
    assert config.repos == ["user/repo1", "user/repo2"]
    assert config.limit == 10


def test_config_file_loading(tmp_path):
    conf_file = tmp_path / "config.yaml"
    conf_file.write_text(yaml.dump({
        "repos": ["org/proj-a", "org/proj-b"],
        "limit": 5,
        "laya_model": "multilingual"
    }))

    config = load_config(config_path=str(conf_file))
    assert config.repos == ["org/proj-a", "org/proj-b"]
    assert config.limit == 5
    assert config.laya_model == "multilingual"


def test_cli_precedence_over_file(tmp_path):
    conf_file = tmp_path / "config.yaml"
    conf_file.write_text(yaml.dump({
        "repos": ["org/file-repo"],
        "limit": 15
    }))

    config = load_config(
        config_path=str(conf_file),
        cli_repos=["org/cli-repo"],
        limit=50
    )
    assert config.repos == ["org/cli-repo"]
    assert config.limit == 50


def test_interactive_config():
    config = load_config(interactive=True)
    assert config.interactive is True

    config_default = load_config()
    assert config_default.interactive is False
