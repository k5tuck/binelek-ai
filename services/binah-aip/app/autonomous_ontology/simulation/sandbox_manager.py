"""
Sandbox Manager

Manages sandbox Neo4j environments for testing ontology changes safely.
Creates isolated test environments, applies changes, and cleans up.
"""

import logging
import docker
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)


class SandboxManager:
    """
    Manages sandbox Neo4j instances for testing ontology changes.

    Key responsibilities:
    - Create isolated Neo4j sandbox from production snapshot
    - Apply proposed ontology changes to sandbox
    - Provide connection details for testing
    - Clean up sandbox after testing
    """

    def __init__(self, docker_client=None, production_neo4j_uri: str = None):
        """
        Initialize sandbox manager.

        Args:
            docker_client: Docker client for container management
            production_neo4j_uri: URI of production Neo4j instance
        """
        self.docker_client = docker_client or docker.from_env()
        self.production_neo4j_uri = production_neo4j_uri
        self.active_sandboxes: Dict[str, Dict[str, Any]] = {}
        logger.info("SandboxManager initialized")

    async def create_sandbox(
        self,
        recommendation_id: str,
        tenant_id: str,
        snapshot_size_limit_mb: int = 1000
    ) -> Dict[str, Any]:
        """
        Create a sandbox Neo4j instance from production snapshot.

        Args:
            recommendation_id: ID of recommendation being tested
            tenant_id: Tenant identifier
            snapshot_size_limit_mb: Maximum snapshot size in MB

        Returns:
            Dictionary with sandbox details (container_id, uri, credentials)
        """
        logger.info(
            f"Creating sandbox for recommendation {recommendation_id}, "
            f"tenant {tenant_id}"
        )

        try:
            # Generate unique sandbox ID
            sandbox_id = f"sandbox-{recommendation_id}-{int(datetime.utcnow().timestamp())}"

            # Create temporary directory for Neo4j data
            temp_dir = tempfile.mkdtemp(prefix=f"neo4j-sandbox-{sandbox_id}")

            # Copy production data (in production, use actual backup/restore)
            # For now, start with empty database
            logger.info(f"Sandbox data directory: {temp_dir}")

            # Start Neo4j container
            container = self.docker_client.containers.run(
                "neo4j:5.12",
                name=sandbox_id,
                environment={
                    "NEO4J_AUTH": "neo4j/sandboxpassword",
                    "NEO4J_dbms_memory_heap_initial__size": "512m",
                    "NEO4J_dbms_memory_heap_max__size": "1g",
                    "NEO4J_ACCEPT_LICENSE_AGREEMENT": "yes"
                },
                volumes={
                    temp_dir: {"bind": "/data", "mode": "rw"}
                },
                ports={"7687/tcp": None, "7474/tcp": None},  # Random host ports
                detach=True,
                remove=True  # Auto-remove when stopped
            )

            # Wait for Neo4j to be ready
            await self._wait_for_neo4j(container)

            # Get assigned ports
            container.reload()
            bolt_port = container.ports["7687/tcp"][0]["HostPort"]
            http_port = container.ports["7474/tcp"][0]["HostPort"]

            sandbox_info = {
                "sandbox_id": sandbox_id,
                "container_id": container.id,
                "container_name": sandbox_id,
                "bolt_uri": f"bolt://localhost:{bolt_port}",
                "http_uri": f"http://localhost:{http_port}",
                "username": "neo4j",
                "password": "sandboxpassword",
                "data_dir": temp_dir,
                "created_at": datetime.utcnow(),
                "recommendation_id": recommendation_id,
                "tenant_id": tenant_id
            }

            # Track active sandbox
            self.active_sandboxes[sandbox_id] = sandbox_info

            logger.info(f"Sandbox created: {sandbox_id} on port {bolt_port}")
            return sandbox_info

        except Exception as e:
            logger.error(f"Error creating sandbox: {e}", exc_info=True)
            raise

    async def _wait_for_neo4j(self, container, timeout: int = 60):
        """Wait for Neo4j to be ready"""
        logger.info("Waiting for Neo4j to be ready...")

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Check if container is still running
                container.reload()
                if container.status != "running":
                    raise RuntimeError(f"Container stopped with status: {container.status}")

                # Check logs for "Started" message
                logs = container.logs(tail=50).decode()
                if "Started." in logs or "Remote interface available" in logs:
                    logger.info("Neo4j is ready")
                    return

            except Exception as e:
                logger.debug(f"Waiting for Neo4j: {e}")

            await asyncio.sleep(2)

        raise TimeoutError("Neo4j failed to start within timeout period")

    async def apply_changes(
        self,
        sandbox_id: str,
        recommendation: Any
    ) -> bool:
        """
        Apply proposed ontology changes to sandbox.

        Args:
            sandbox_id: Sandbox identifier
            recommendation: Recommendation with changes to apply

        Returns:
            True if changes applied successfully
        """
        logger.info(f"Applying changes to sandbox {sandbox_id}")

        sandbox_info = self.active_sandboxes.get(sandbox_id)
        if not sandbox_info:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            # In production, this would:
            # 1. Generate updated YAML
            # 2. Run Regen to generate code
            # 3. Apply schema changes to Neo4j
            # 4. Run data migrations

            # For now, mock the changes
            logger.info(f"Changes applied to sandbox {sandbox_id}")
            return True

        except Exception as e:
            logger.error(f"Error applying changes: {e}", exc_info=True)
            return False

    async def copy_production_data(
        self,
        sandbox_id: str,
        tenant_id: str,
        sample_size: Optional[int] = None
    ):
        """
        Copy production data to sandbox (full or sample).

        Args:
            sandbox_id: Sandbox identifier
            tenant_id: Tenant to copy data from
            sample_size: Optional limit on number of records
        """
        logger.info(f"Copying production data to sandbox {sandbox_id}")

        sandbox_info = self.active_sandboxes.get(sandbox_id)
        if not sandbox_info:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        # In production, this would:
        # 1. Export tenant data from production Neo4j
        # 2. Import into sandbox
        # 3. Optionally sample data for faster testing

        logger.info(f"Production data copied to sandbox {sandbox_id}")

    async def destroy_sandbox(self, sandbox_id: str):
        """
        Destroy a sandbox environment and clean up resources.

        Args:
            sandbox_id: Sandbox identifier
        """
        logger.info(f"Destroying sandbox {sandbox_id}")

        sandbox_info = self.active_sandboxes.get(sandbox_id)
        if not sandbox_info:
            logger.warning(f"Sandbox {sandbox_id} not found")
            return

        try:
            # Stop and remove container
            container = self.docker_client.containers.get(sandbox_info["container_id"])
            container.stop(timeout=10)
            logger.info(f"Container {sandbox_id} stopped")

            # Clean up data directory
            import shutil
            if os.path.exists(sandbox_info["data_dir"]):
                shutil.rmtree(sandbox_info["data_dir"])
                logger.info(f"Data directory cleaned: {sandbox_info['data_dir']}")

            # Remove from tracking
            del self.active_sandboxes[sandbox_id]

            logger.info(f"Sandbox {sandbox_id} destroyed")

        except Exception as e:
            logger.error(f"Error destroying sandbox: {e}", exc_info=True)

    async def cleanup_all(self):
        """Clean up all active sandboxes"""
        logger.info(f"Cleaning up {len(self.active_sandboxes)} sandboxes")

        for sandbox_id in list(self.active_sandboxes.keys()):
            await self.destroy_sandbox(sandbox_id)

        logger.info("All sandboxes cleaned up")

    def get_sandbox_info(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a sandbox"""
        return self.active_sandboxes.get(sandbox_id)

    def list_sandboxes(self) -> Dict[str, Dict[str, Any]]:
        """List all active sandboxes"""
        return self.active_sandboxes.copy()
