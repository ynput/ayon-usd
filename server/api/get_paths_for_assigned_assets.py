"""Get the asset paths assigned to a given user."""
from __future__ import annotations

from ayon_server.api.dependencies import ClientSiteID, CurrentUser
from ayon_server.helpers.roots import get_roots_for_projects
from ayon_server.lib.postgres import Postgres
from ayon_server.logging import logger

from server.models import EntityPathList, ResolvedPair

from .router import router
from .templating import StringTemplate


def get_representation_path(
        template: str,
        context: dict,
        roots: dict[str, str] | None = None,
) -> str:
    """Get asset paths assigned to the user.

    Args:
        template: Template
        context: Context
        roots: dict[str, str] | None

    Returns:
        str: Resolved path

    """
    context["root"] = roots or {}
    return StringTemplate.format_template(template, context)

@router.get("/{project_name}/assigned_paths_for/{user_name}")
async def get_assigned_asset_paths(
        user: CurrentUser,
        user_name: str,
        project_name: str,
        site_id: ClientSiteID,
) -> EntityPathList:
    """Get asset paths assigned to the user.

    Args:
        user: CurrentUser
        user_name: User name
        project_name: Project name
        site_id: Site ID

    Returns:
        EntityPathList: A new instance of EntityPathList

    """
    async with Postgres.transaction():
        query = f"""
            SELECT 
                DISTINCT r.id AS representation_id,
                r.attrib->>'template' AS file_template,
                r.data->'context' as context,
                r.name AS repre,
                v.version, h.path, p.name AS product
            FROM project_{project_name}.representations r
                JOIN project_{project_name}.versions v ON r.version_id = v.id
                JOIN project_{project_name}.products p ON v.product_id = p.id
                JOIN project_{project_name}.tasks t ON t.folder_id = p.folder_id
                JOIN project_{project_name}.hierarchy h ON h.id = p.folder_id
            WHERE t.assignees @> ARRAY[$1]::VARCHAR[];
        """  # noqa: S608
        logger.debug(f"query: {query}")
        logger.debug(
            f"site: {site_id}, project: {project_name}, user: {user.name}")
        result: list[ResolvedPair] = []
        roots = {}
        # roots = await get_roots_for_projects(
        #   user_name, site_id, [project_name])
        async for row in Postgres.iterate(query, user_name):
            path = row["path"]
            version = row["version"]
            version_name = f"v{version:03d}"  # this should follow padding
            uri = f"ayon+entity://{project_name}/{path}"
            uri += f"?product={row['product']}&version={version_name}&representation={row['repre']}"  # noqa: E501
            if row["file_template"]:
                file_path = get_representation_path(row["file_template"],
                    row["context"] or {},
                    roots=roots.get(project_name, {})
                )
            else:
                # this should handle representation traits in time
                continue

            result.append(ResolvedPair(uri=uri, path=file_path))
    return EntityPathList(path_list=result)
