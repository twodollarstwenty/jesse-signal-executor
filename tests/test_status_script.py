import json
import os
import subprocess
from pathlib import Path


def test_status_script_executes_from_non_repo_root_with_expected_compose_calls(tmp_path: Path):
    status_script = Path(__file__).resolve().parent.parent / "scripts" / "status.sh"
    docker_log = tmp_path / "docker-calls.jsonl"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "log_path = Path(os.environ['FAKE_DOCKER_LOG'])\n"
        "with log_path.open('a', encoding='utf-8') as fh:\n"
        "    fh.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "print('fake docker output: ' + ' '.join(sys.argv[1:]))\n"
    )
    fake_docker.chmod(0o755)

    run_cwd = tmp_path / "outside-repo"
    run_cwd.mkdir()
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(docker_log)

    result = subprocess.run(
        ["bash", str(status_script)],
        cwd=run_cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "fake docker output: compose ps\n"

    calls = [json.loads(line) for line in docker_log.read_text().splitlines()]
    assert calls == [["compose", "ps"]]
