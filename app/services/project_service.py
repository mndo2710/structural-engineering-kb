"""ProjectService: Application workflow service for projects, groups, and calculation items.

Conforms to SAD v1.1 Section 7.2 & WP-1b.
Coordinates pure-Python WorkspaceController and GUI requests with SQLite Schema v2 ProjectRepository.
"""

from typing import Any, Dict, List, Optional, Union

from app.models import CalculationResult, CalculationStatus, DesignMethod
from app.registry import ModuleMaturity, ModuleRegistry, get_module_registry
from storage.repositories.project_repository import ProjectRepository


_DEFAULT_GROUPS = ("Roof framing", "Level 2", "Level 1", "Foundations")


class ProjectService:
    """Manages active project sessions, groups, ordered calculation items, and defaults."""

    def __init__(
        self,
        repository: Optional[ProjectRepository] = None,
        registry: Optional[ModuleRegistry] = None,
    ) -> None:
        self.repository = repository or ProjectRepository()
        self.registry = registry or get_module_registry()
        self._active_project_id: Optional[str] = None

    @property
    def active_project_id(self) -> Optional[str]:
        return self._active_project_id

    def _resolve_project_id(self, project_id: Optional[str]) -> str:
        p_id = project_id or self._active_project_id
        if not p_id:
            raise ValueError("No active project. Specify project_id or activate a project first.")
        return p_id

    # --------------------------------------------------------------------------
    # Project Lifecycle & Defaults
    # --------------------------------------------------------------------------
    def ensure_active_project(
        self,
        default_name: str = "Smith Residence",
        default_code: str = "PRJ-2026-001",
        default_engineer: str = "Senior Structural Engineer, PE",
    ) -> Dict[str, Any]:
        """Return active project, activate the most recent project, or create a default project with groups."""
        if self._active_project_id:
            prj = self.repository.get_project(self._active_project_id)
            if prj is not None:
                return prj

        existing = self.repository.list_projects(active_only=True)
        if existing:
            self._active_project_id = existing[0]["project_id"]
            return existing[0]

        project = self.create_project(
            name=default_name,
            code=default_code,
            engineer=default_engineer,
            set_as_active=True,
        )
        p_id = project["project_id"]
        for group_name in _DEFAULT_GROUPS:
            self.create_group(group_name, project_id=p_id)
        return project

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
        set_as_active: bool = True,
    ) -> Dict[str, Any]:
        """Create new structural engineering project and optionally activate it."""
        project = self.repository.create_project(
            name=name,
            code=code,
            client=client,
            engineer=engineer,
            description=description,
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

    def get_project_defaults(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve default design method and effective code registry for the project."""
        p_id = self._resolve_project_id(project_id)
        settings = self.repository.get_project_settings(p_id)
        if settings is None:
            raise ValueError(f"Project '{p_id}' does not exist.")
        return settings

    def set_project_defaults(
        self,
        default_design_method: Union[str, DesignMethod],
        code_registry: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist default design method and code registry overrides for the project."""
        p_id = self._resolve_project_id(project_id)
        return self.repository.upsert_project_settings(
            project_id=p_id,
            default_design_method=default_design_method,
            code_registry_json=code_registry,
        )

    # --------------------------------------------------------------------------
    # Calculation Groups (WP-1b)
    # --------------------------------------------------------------------------
    def list_groups(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List ordered calculation groups for the specified or active project."""
        p_id = self._resolve_project_id(project_id)
        return self.repository.list_groups(p_id)

    def ensure_group(self, name: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Return existing group matching case-insensitive name in project, or create it."""
        p_id = self._resolve_project_id(project_id)
        clean = name.strip()
        if not clean:
            raise ValueError("Group name must not be empty.")
        target_lower = clean.lower()
        for grp in self.repository.list_groups(p_id):
            if grp["name"].strip().lower() == target_lower:
                return grp
        return self.repository.create_group(project_id=p_id, name=clean)

    def create_group(
        self,
        name: str,
        project_id: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a calculation group in the specified or active project."""
        p_id = self._resolve_project_id(project_id)
        return self.repository.create_group(project_id=p_id, name=name, sort_order=sort_order)

    def rename_group(self, group_id: str, name: str) -> bool:
        """Rename a calculation group."""
        self.repository.rename_group(group_id, name)
        return True

    def move_group(self, group_id: str, new_index: int) -> bool:
        """Atomically reorder a calculation group to 0-based index."""
        self.repository.move_group(group_id, new_index)
        return True

    def set_group_collapsed(self, group_id: str, collapsed: bool) -> bool:
        """Persist expanded/collapsed state for a calculation group."""
        self.repository.set_group_collapsed(group_id, collapsed)
        return True

    def delete_group(self, group_id: str) -> bool:
        """Delete a group while moving its items to ungrouped."""
        return self.repository.delete_group(group_id)

    # --------------------------------------------------------------------------
    # Calculation Item CRUD, Ordering, Drafts & Revisions (WP-1b)
    # --------------------------------------------------------------------------
    def list_items(
        self,
        project_id: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """List ordered calculation items for the specified or active project."""
        p_id = self._resolve_project_id(project_id)
        return self.repository.list_calculations_for_project(p_id, include_deleted=include_deleted)

    def add_item(
        self,
        module_id: str,
        title: str,
        group_id: Optional[str] = None,
        group_name: Optional[str] = None,
        start_from: str = "blank",
        source_item_id: Optional[str] = None,
        design_method: Optional[Union[str, DesignMethod]] = None,
        draft_inputs: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        allow_unverified: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a new calculation item to a project using ModuleRegistry metadata.
        Supports 'blank' (empty inputs, INCOMPLETE) and 'duplicate' (copies draft only, 0 revisions).
        """
        p_id = self._resolve_project_id(project_id)
        try:
            spec = self.registry.resolve(module_id)
        except KeyError as exc:
            raise ValueError(f"Unknown calculation module '{module_id}'.") from exc

        if spec.maturity in (ModuleMaturity.COMING_SOON, ModuleMaturity.UNAVAILABLE) and not allow_unverified:
            raise ValueError(
                f"Calculation module '{spec.module_id}' is {spec.maturity.value} and cannot be created yet."
            )

        resolved_group_id = group_id
        if resolved_group_id is None and group_name is not None and group_name.strip():
            resolved_group_id = self.ensure_group(group_name, project_id=p_id)["group_id"]

        mode = str(start_from or "blank").strip().lower()
        if mode == "duplicate" and source_item_id:
            return self.duplicate_item(
                source_item_id,
                new_title=title,
                group_id=resolved_group_id,
            )

        if design_method is not None:
            effective_method: Union[str, DesignMethod] = design_method
        else:
            effective_method = self.get_project_defaults(p_id).get("default_design_method", "ASD")

        code_edition = self.registry.resolve_code_display(spec.module_id)
        initial_draft = dict(draft_inputs) if draft_inputs is not None else {}

        return self.repository.create_calculation(
            project_id=p_id,
            module_id=spec.module_id,
            title=title,
            code_edition=code_edition,
            design_method=effective_method,
            group_id=resolved_group_id,
            draft_inputs=initial_draft,
            status=CalculationStatus.INCOMPLETE,
        )

    def duplicate_item(
        self,
        item_id: str,
        new_title: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Duplicate draft inputs and settings into a new item with 0 revisions."""
        return self.repository.duplicate_calculation(
            source_calculation_id=item_id,
            new_title=new_title,
            group_id=group_id,
        )

    def move_item(self, item_id: str, group_id: Optional[str], new_index: int) -> bool:
        """Atomically move/reorder a calculation item into target group at 0-based index."""
        self.repository.move_calculation(item_id, target_group_id=group_id, new_index=new_index)
        return True

    def rename_item(self, item_id: str, title: str) -> bool:
        """Rename a calculation item."""
        self.repository.rename_calculation(item_id, title)
        return True

    def delete_item(self, item_id: str) -> bool:
        """Soft-delete a calculation item while preserving immutable revision history."""
        return self.repository.soft_delete_calculation(item_id)

    def save_draft(
        self,
        item_id: str,
        draft_inputs: Dict[str, Any],
        design_method: Optional[Union[str, DesignMethod]] = None,
        code_edition: Optional[str] = None,
        status: Optional[Union[str, CalculationStatus]] = None,
    ) -> Dict[str, Any]:
        """Autosave draft inputs and metadata without creating a revision."""
        return self.repository.update_draft(
            calculation_id=item_id,
            draft_inputs=draft_inputs,
            design_method=design_method,
            code_edition=code_edition,
            status=status,
        )

    def update_item_run_state(
        self,
        item_id: str,
        last_dcr: Optional[float],
        status: Union[str, CalculationStatus],
        last_input_hash: Optional[str],
    ) -> Dict[str, Any]:
        """Update cached run DCR/status/hash without creating a revision."""
        return self.repository.update_run_state(
            calculation_id=item_id,
            last_dcr=last_dcr,
            status=status,
            last_input_hash=last_input_hash,
        )

    def create_calculation(
        self,
        module_id: str,
        title: str,
        code_edition: str,
        design_method: Union[str, DesignMethod],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calculation container within the specified or active project."""
        p_id = self._resolve_project_id(project_id)
        return self.repository.create_calculation(
            project_id=p_id,
            module_id=module_id,
            title=title,
            code_edition=code_edition,
            design_method=design_method,
        )

    def save_calculation_run(
        self,
        calculation_id: str,
        calc_result: CalculationResult,
        change_notes: str = "",
        engineer: str = "",
        reference_manifest_sha256: Optional[str] = None,
        reference_snapshot: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        input_hash: Optional[str] = None,
    ) -> int:
        """Save a new immutable calculation revision."""
        eng = engineer
        if not eng and self._active_project_id:
            prj = self.get_active_project()
            if prj:
                eng = prj.get("engineer", "")

        return self.repository.save_calculation_run(
            calculation_id=calculation_id,
            calc_result=calc_result,
            change_notes=change_notes,
            engineer=eng,
            reference_manifest_sha256=reference_manifest_sha256,
            reference_snapshot=reference_snapshot,
            input_hash=input_hash,
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
