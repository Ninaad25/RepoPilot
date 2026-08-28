import os

import requests


class SandboxRunnerClient:

    def __init__(self):
        self.runner_url = os.getenv(
            "SANDBOX_RUNNER_URL",
            "",
        ).rstrip("/")

        self.runner_api_key = os.getenv(
            "RUNNER_API_KEY",
            "",
        )

        if not self.runner_url:
            raise RuntimeError(
                "SANDBOX_RUNNER_URL is not configured"
            )

        if not self.runner_api_key:
            raise RuntimeError(
                "RUNNER_API_KEY is not configured"
            )

    # ==================================================
    # HEADERS
    # ==================================================

    def _headers(self):
        return {
            "Authorization": (
                f"Bearer {self.runner_api_key}"
            ),
            "Content-Type": "application/json",
        }

    # ==================================================
    # LAUNCH
    # ==================================================

    def launch(
        self,
        sandbox_id: str,
        repo_url: str,
        container_port: int = 3000,
    ):

        response = requests.post(
            f"{self.runner_url}/runner/launch",
            headers=self._headers(),
            json={
                "sandbox_id": sandbox_id,
                "repo_url": repo_url,
                "container_port": container_port,
            },
            timeout=900,
        )

        if response.status_code != 200:

            try:
                detail = response.json().get(
                    "detail",
                    response.text,
                )
            except Exception:
                detail = response.text

            raise RuntimeError(
                f"Runner launch failed: {detail}"
            )

        return response.json()

    # ==================================================
    # STOP
    # ==================================================

    def stop(
        self,
        sandbox_id: str,
        container_name: str,
    ):

        response = requests.post(
            f"{self.runner_url}/runner/stop",
            headers=self._headers(),
            json={
                "sandbox_id": sandbox_id,
                "container_name": container_name,
            },
            timeout=60,
        )

        if response.status_code != 200:

            try:
                detail = response.json().get(
                    "detail",
                    response.text,
                )
            except Exception:
                detail = response.text

            raise RuntimeError(
                f"Runner stop failed: {detail}"
            )

        return response.json()