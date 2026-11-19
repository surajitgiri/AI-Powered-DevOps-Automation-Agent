import logging
import shutil
import tarfile
import uuid

from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubCloneService:

    def __init__(self):

        self.workspace_root = Path(
            settings.GITHUB_CLONE_WORKSPACE
        ).resolve()

        self.workspace_root.mkdir(
            parents = True,
            exist_ok = True
        )

        self.max_archive_size = (
            settings.GITHUB_MAX_ARCHIVE_SIZE_MB
            *1024
            *1024
        )
    
    # ----------------------------------
    # 1. Validate repository information
    # ----------------------------------
    def validate_repository(self, repository_full_name):

        parts = repository_full_name.split("/")

        if len(parts) != 2:

            raise ValueError(
                "Invalid GitHub repository name"
            )
        
        owner, repository = parts

        if not all(
            part and part not in (".", "..")
            and all(
                char.isalnum() or char in "-_."
                for char in part
            )
            for part in parts
        ):

            raise ValueError(
                "Invalid repository owner or name"
            )
        return owner, repository
    
    # ----------------------------------
    # 2. Validate branch
    # ----------------------------------
    def validate_branch(self, branch):

        if not branch or len(branch) > 200:

            raise ValueError(
                "Invalid branch name"
            )
        
        if (
            branch.startswith("/")
            or ".." in branch
            or branch.startswith("-")
            or any(char in branch for char in ("\\", "\0", " "))
        ):

            raise ValueError(
                "Invalid branch name"
            )
        
        return branch
    
    # ----------------------------------
    # 3. Download repository archive
    # ----------------------------------
    def download_repository(
        self,
        access_token,
        owner,
        repository,
        branch
    ):

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repository}/tarball/{branch}"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",

            "Accept": "application/vnd.github+json",

            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:

            with httpx.Client(
                timeout = 60,
                follow_redirects = True
            ) as client:

                with client.stream(
                    "GET",
                    url,
                    headers = headers
                ) as response:

                    response.raise_for_status()

                    content_length = response.headers.get(
                        "content-length"
                    )

                    if (
                        content_length
                        and int(content_length) > self.max_archive_size
                    ):

                        raise ValueError(
                            "Repository archive exceeds size limit"
                        )
                    
                    archive_data = bytearray()

                    for chunk in response.iter_bytes():

                        archive_data.extend(chunk)

                        if len(archive_data) > self.max_archive_size:

                            raise ValueError(
                                "Repository archive exceeds size limit"
                            )
                    
                    return bytes(archive_data)

        except httpx.HTTPStatusError as exc:

            logger.exception(
                "GitHub archive download failed"
            )

            status = exc.response.status_code

            if status == 404:

                raise ValueError(
                    "Repository or branch not found, "
                    "or GitHub token lacks repository access"
                )
            
            if status == 401:

                raise ValueError(
                    "GitHub authentication failed"
                )
            
            if status == 403:

                raise ValueError(
                    "GitHub API access forbidden or rate limited"
                )
            
            raise RuntimeError(
                f"GitHub archive request failed: HTTP {status}"
            )
        
        except httpx.HTTPError:

            logger.exception(
                "GitHub network error"
            )

            raise RuntimeError(
                "Unable to download GitHub repository"
            )

    # ----------------------------------
    # 4. Extract repository archive
    # ----------------------------------
    def extract_archive(
        self,
        archive_data,
        destination
    ):

        destination.mkdir(
            parents=True,
            exist_ok=True
        )

        archive_path = destination / "repository.tar.gz"

        try:

            archive_path.write_bytes(
                archive_data
            )

            with tarfile.open(
                archive_path,
                mode = "r:gz"
            ) as archive:

                members = archive.getmembers()

                if len(members) > 20000:

                    raise ValueError(
                        "Repository contains too many files"
                    )
                
                for member in members:

                    if (
                        member.issym()
                        or member.islnk()
                    ):

                        raise ValueError(
                            "Repository archive contains links"
                        )
                
                # Python 3.12+ safe extraction filter
                archive.extractall(
                    path = destination,
                    filter = "data"
                )
            
            extracted_roots = [
                item for item in destination.iterdir()
                if item.is_dir()
            ]

            if len(extracted_roots) != 1:

                raise ValueError(
                    "Unexpected GitHub archive structure"
                )
            
            source_directory = extracted_roots[0]

            return source_directory
        
        except (tarfile.TarFile, OSError):

            logger.exception(
                "Repository archive extraction failed"
            )

            raise RuntimeError(
                "Unable to extract repository archive"
            )

        finally:

            archive_path.unlink(
                missing_ok = True
            )


    # ----------------------------------
    # 5. Analyze repository structure
    # ----------------------------------
    def analyze_repository(self, repository_path):

        files = {
            "package_json": (
                repository_path / "package.json"
            ).exists(),

            "package_lock": (
                repository_path / "package-lock.json"
            ).exists(),

            "yarn_lock": (
                repository_path / "yarn.lock"
            ).exists(),

            "pnpm_lock": (
                repository_path / "pnpm-lock.yaml"
            ).exists(),

            "requirements_txt": (
                repository_path / "requirements.txt"
            ).exists(),

            "pyproject_toml": (
                repository_path / "pyproject.toml"
            ).exists(),

            "dockerfile": (
                repository_path / "Dockerfile"
            ).exists(),

            "dockerignore": (
                repository_path / ".dockerignore"
            ).exists(),

            "readme": (
                repository_path / "README.md"
            ).exists()

        }

        framework = "unknown"

        package_json = repository_path / "package.json"

        if package_json.exists():

            import json

            try:

                package = json.loads(
                    package_json.read_text(
                        encoding = "utf-8"
                    )
                )

                dependencies = {
                    **package.get("dependencies", {}),
                    **package.get("devDependencies", {})
                }

                if "next" in dependencies:

                    framework = "nextjs"

                elif "express" in dependencies:

                    framework = "nodejs"

                elif "fastify" in dependencies:

                    framework = "nodejs"

                else:

                    framework = "nodejs"
            
            except Exception:

                logger.warning(
                    "Unable to parse package.json"
                )

        elif (
            files["requirements_txt"]
            or files["pyproject_toml"]
        ):

            framework = "python"
        
        return {
            "framework": framework,

            "files": files
        }
    
    # ----------------------------------
    # 6. Clone repository
    # ----------------------------------
    def clone_repository(
        self,
        access_token,
        repository_full_name,
        branch,
        user_id,
        project_id
    ):  

        owner, repository = self.validate_repository(
            repository_full_name
        )

        branch = self.validate_branch(
            branch
        )

        workspace_id = str(
            uuid.uuid4()
        )

        workspace = (
            self.workspace_root
            / str(user_id)
            / str(project_id)
            / workspace_id
        )

        # Keep temp download dir BESIDE workspace (not inside it).
        # If it were a child, mkdir(parents=True) on it would create
        # `workspace` itself, causing shutil.move to move INTO the dir
        # instead of renaming it — breaking on Windows.
        temporary_directory = (
            self.workspace_root
            / str(user_id)
            / str(project_id)
            / f"{workspace_id}_download"
        )

        try:

            logger.info(
                "Downloading repository %s branch %s",
                repository_full_name,
                branch
            )

            archive_data = self.download_repository(
                access_token=access_token,

                owner=owner,

                repository=repository,

                branch=branch
            )

            extracted_directory = self.extract_archive(
                archive_data=archive_data,

                destination=temporary_directory
            )

            # Move repository files into final workspace
            # On Windows, Path.rename() fails if the target already exists.
            # Use shutil.move() after removing any stale target directory.
            if workspace.exists():
                shutil.rmtree(workspace)
            shutil.move(str(extracted_directory), str(workspace))

            shutil.rmtree(
                temporary_directory,
                ignore_errors = True
            )

            analysis = self.analyze_repository(
                workspace
            )

            logger.info(
                "Repository prepared successfully: %s",
                workspace_id
            )

            return {
                "workspace_id": workspace_id,

                "repository": repository_full_name,

                "branch": branch,

                "framework": analysis["framework"],

                "files": analysis["files"]
            }
        
        except Exception:

            shutil.rmtree(
                workspace,
                ignore_errors=True
            )

            shutil.rmtree(
                temporary_directory,
                ignore_errors=True
            )

            logger.exception(
                "Repository preparation failed"
            )

            raise

github_clone_service = GitHubCloneService()