from pathlib import Path


def test_jesse_runtime_bootstrap_files_exist():
    assert Path("runtime/jesse_workspace/requirements.txt").exists()
    assert Path("runtime/jesse_workspace/.env.example").exists()


def test_signal_dockerfile_installs_runtime_jesse_requirements():
    dockerfile = Path("infra/docker/signal.Dockerfile").read_text()

    assert "runtime/jesse_workspace/requirements.txt" in dockerfile
