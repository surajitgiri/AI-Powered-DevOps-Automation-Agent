import base64
import json
import logging

from app.services.github_service import GitHubService

logger = logging.getLogger(__name__)

class DockerfileGeneratorService:

    def __init__(self):

        self.github_service = GitHubService()
    
    # -----------------------------------
    # 1. Retrieve GitHub Repository Files
    # -----------------------------------
    def get_repository_file(
        self,
        access_token: str,
        owner: str,
        repository: str,
        filename: str,
        branch: str
    ): 

        try:

            endpoint = (
                f"/repos/{owner}/{repository}/contents/{filename}"
                f"?ref={branch}"
            )

            response = self.github_service.github_request(
                access_token,
                endpoint
            )

            if not isinstance(response, dict):
                return None

            if response.get("type") != "file":
                return None
            
            content = response.get("content")

            if not content:
                return None
            
            decode = base64.b64decode(
                content
            ).decode("utf-8")

            return decode

        except Exception as exc:

            logger.warning(
                "Unable to retrieve repository file %s: %s",
                filename,
                exc
            )

            return None

    # -----------------------------------
    # 2. Detect Application Framework
    # -----------------------------------
    def detect_framework(
        self,
        package_json=None,
        requirements_txt=None,
        pyproject_toml=None,
        application_type=None
    ):

        if application_type:

            return application_type
        
        if package_json:

            try:

                package = json.loads(package_json)

                dependencies = {
                    **package.get("dependencies", {}),
                    **package.get("devDependencies", {})
                }

                if "next" in dependencies:

                    return "nextjs"
                if "express" in dependencies:

                    return "nodejs"

                if "fastify" in dependencies:

                    return "nodejs"

                return "nodejs"
            
            except json.JSONDecodeError:

                logger.warning(
                    "Invalid package.json"
                )
        
        python_dependencies = (
            (requirements_txt or "")
            + "\n"
            + (pyproject_toml or "")
        ).lower()

        if "fastapi" in python_dependencies:

            return "fastapi"
        
        if "uvicorn" in python_dependencies:

            return "fastapi"
        
        raise ValueError(
            "Unable to detect application framework. "
            "Specify application_type manually."
        )
    
    # -----------------------------------
    # 3. Generate Next.js Dockerfile
    # -----------------------------------
    def nextjs_dockerfile(self):

           return """
            FROM node:22-alpine AS builder

            WORKDIR /app

            COPY package*.json ./

            RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

            COPY . .

            ENV NEXT_TELEMETRY_DISABLED=1

            RUN npm run build

            FROM node:22-alpine

            WORKDIR /app

            ENV NODE_ENV=production

            ENV NEXT_TELEMETRY_DISABLED=1

            ENV PORT=3000

            COPY --from=builder /app ./

            EXPOSE 3000

            CMD ["npm", "start"]
            """.strip()
       
    # -----------------------------------
    # 4. Generate Node.js Dockerfile
    # -----------------------------------
    def nodejs_dockerfile(self):

        return """
        FROM node:22-alpine

        WORKDIR /app

        COPY package*.json ./

        RUN npm ci --omit=dev

        COPY . .

        ENV NODE_ENV=production

        EXPOSE 5000

        CMD ["npm", "start"]
        """.strip()
    
    # -----------------------------------
    # 5. Generate FastAPI Dockerfile
    # -----------------------------------
    def fastapi_dockerfile(self):

        return """

        FROM python: 3.12-slim

        WORKDIR /app

        ENV PYTHONDONTWRITEBYTECODE = 1

        ENV PYTHONUNBUFFERED = 1

        COPY requirements.txt .

        RUN pip install --no-cache-dir -r requirements.txt

        COPY . .

        EXPOSE 8000

        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        """.strip()

    # -----------------------------------
    # 6. Generate Dockerfile
    # -----------------------------------
    def generate_dockerfile(self, framework):

        templates = {
            "nextjs": self.nextjs_dockerfile,

            "nodejs": self.nodejs_dockerfile,

            "fastapi": self.fastapi_dockerfile

        }

        generator = templates.get(framework)

        if not generator:

            raise ValueError(
                "Unsupported application framework"
            )

        return generator()

    # -----------------------------------
    # 7. Generate .dockerignore
    # -----------------------------------
    def generate_dockerignore(self, framework):

        common = """
        .git
        .gitignore
        .env
        .env.*
        !.env.example
        node_modules
        __pycache__
        *.pyc
        .pytest_cache
        .venv
        venv
        coverage
        .DS_Store
        .idea
        .vscode
        *.log
        """

        if framework == "nextjs":

            common += """
            .next
            out
            build
            """
        elif framework == "fastapi":

            common += """
            .mypy_cache
            .ruff_cache
            """

        return common.strip()

    # -----------------------------------
    # 8. Complete Generation Workflow
    # -----------------------------------
    def generate(
        self,
        access_token,
        repository_full_name,
        branch,
        application_type = None
    ):

        try:

            owner, repository = (
                repository_full_name.split("/", 1)
            )

            # Retrieve important repository files
            package_json = self.get_repository_file(
                access_token,
                owner,
                repository,
                "package.json",
                branch
            )

            requirements_txt = self.get_repository_file(
                access_token,
                owner,
                repository,
                "requirements.txt",
                branch
            )

            pyproject_toml = self.get_repository_file(
                access_token,
                owner,
                repository,
                "pyproject.toml",
                branch
            )

            # detect framework
            framework = self.detect_framework(
                package_json = package_json,
                requirements_txt = requirements_txt,
                pyproject_toml = pyproject_toml,
                application_type = application_type
            )

            # Generate Docker files
            dockerfile = self.generate_dockerfile(
                framework
            )

            dockerignore = self.generate_dockerignore(
                framework
            )

            return {
                "repository": repository_full_name,

                "framework": framework,

                "dockerfile": dockerfile,

                "dockerignore": dockerignore

            }
        
        except Exception:

            logger.exception(
                "Dockerfile generation failed"
            )

            raise

dockerfile_generator = DockerfileGeneratorService()