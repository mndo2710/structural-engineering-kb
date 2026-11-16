"""ProjectService: Application workflow service for managing projects and calculation sets.

Conforms to SAD v1.0 Section 7.2.
Coordinates GUI requests with ProjectRepository.
"""

from typing import Any, Dict, List, Optional, Union
from core.common.calculation_result import CalculationResult, DesignMethod
from storage.repositories.project_repository import ProjectRepository


class ProjectService:
    """Manages active project sessions and coordinates project database operations."""

    def __init__(self, repository: Optional[ProjectRepository] = None) -> None:
        self.repository = repository or ProjectRepository()
        self._active_project_id: Optional[str] = None

    @property
    def active_project_id(self) -> Optional[str]:
        return self._active_project_id

    def set_active_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Set active project for the current session."""
        prj = self.repository.get_project(project_id)
        if prj:
            self._active_project_id = project_id
            return prj
        raise ValueError(f"Project '{project_id}' does not exist.")

    def get_active_project(self) -> Optional[Dict[str, Any]]:
        """Retrieve active project details."""
        if not self._active_project_id:
            return None
        return self.repository.get_project(self._active_project_id)

    def create_project(
        self,
        name: str,
        code: Optional[str] = None,
        client: str = "",
        engineer: str = "",
        description: str = "",
        set_as_active: bool = True
    ) -> Dict[str, Any]:
        """Create new structural engineering project and optionally activate it."""
        project = self.repository.create_project(
            name=name,
            code=code,
            client=client,
            engineer=engineer,
            description=description
        )
        if set_as_active:
            self._active_project_id = project["project_id"]
        return project

    def list_projects(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all available projects."""
        return self.repository.list_projects(active_only=active_only)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project by ID."""
        return self.repository.get_project(project_id)

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Update metadata of an existing project."""
        return self.repository.update_project(project_id, updates)

    def delete_project(self, project_id: str) -> bool:
        """Delete project and associated calculations."""
        if self._active_project_id == project_id:
            self._active_project_id = None
        return self.repository.delete_project(project_id)

    def create_calculation(
        self,
        module_id: str,
        title: str,
        code_edition: str,
        design_method: Union[str, DesignMethod],
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new calculation container within the specified or active project."""
        p_id = project_id or self._active_project_id
        if not p_id:
            raise ValueError("No active project. Specify project_id or activate a project first.")
        return self.repository.create_calculation(
            project_id=p_id,
            module_id=module_id,
            title=title,
            code_edition=code_edition,
            design_method=design_method
        )

    def save_calculation_run(
        self,
        calculation_id: str,
        calc_result: CalculationResult,
        change_notes: str = "",
        engineer: str = ""
    ) -> int:
        """Save a new calculation revision."""
        eng = engineer
        if not eng and self._active_project_id:
            prj = self.get_active_project()
            if prj:
                eng = prj.get("engineer", "")

        return self.repository.save_calculation_run(
            calculation_id=calculation_id,
            calc_result=calc_result,
            change_notes=change_notes,
            engineer=eng
        )

    def list_calculations(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List calculations for a project (defaults to active project)."""
        p_id = project_id or self._active_project_id
        if not p_id:
            return []
        return self.repository.list_calculations_for_project(p_id)

    def get_calculation(self, calculation_id: str) -> Optional[Dict[str, Any]]:
        """Get calculation by ID."""
        return self.repository.get_calculation(calculation_id)
