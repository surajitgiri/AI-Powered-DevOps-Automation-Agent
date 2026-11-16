from pathlib import Path
from app.services.docker_service import DockerService

def test_docker_connection():

    service = DockerService()
    result = service.health_check()

    print(result)

    assert result["status"] == "healthy"

    service.close()

def test_docker_build():

    service = DockerService()

    workspace = Path(
        service.workspace_root / "test-project"
    )

    workspace.mkdir(
        parents=True,
        exist_ok=True
    )

    dockerfile = workspace / "Dockerfile"

    dockerfile.write_text(
        """
        FROM python:3.12-slim

        WORKDIR /app

        RUN python --version

        CMD ["python", "--version"]
        """
    )

    result = service.build_image(
        context_path = str(workspace),
        image_name = "opspilot-test",
        image_tag = "v1"
    )

    assert result["success"] is True

    assert result["image_id"] is not None

    service.close()