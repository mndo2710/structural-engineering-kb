"""Unit tests for SQLite ProjectRepository, ProjectService, and HistoryService per SAD v1.0 Section 9."""

import tempfile
import uuid
from pathlib import Path
import pytest

from core.common.calculation_result import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
from storage.repositories.project_repository import ProjectRepository
from app.services.project_service import ProjectService
from app.services.history_service import HistoryService


@pytest.fixture
def temp_repo():
    tmp_file = Path(tempfile.gettempdir()) / f"test_struct_{uuid.uuid4().hex}.sqlite3"
    repo = ProjectRepository(db_path=tmp_file)
    yield repo
    if tmp_file.exists():
        try:
            tmp_file.unlink()
        except OSError:
            pass


@pytest.fixture
def sample_result():
    ls1 = LimitStateResult(
        step_id="S1",
        name="Flexural Yielding",
        code_clause="AISC 360-22 Sec. F2.1",
        equation_latex="M_n = F_y \\cdot Z_x",
        substitution_str="50 ksi * 10 in^3",
        demand=300.0,
        capacity=500.0,
        units="kip-in.",
        dcr=0.60,
        status=CalculationStatus.PASS
    )
    return CalculationResult(
        calculation_id="calc-001",
        module_id="steel_beam",
        code_edition="AISC 360-22",
        design_method=DesignMethod.ASD,
        input_parameters={"span_ft": 15.0, "section": "W10x30", "fy_ksi": 50.0},
        assumptions=["Fully braced lateral torsional buckling"],
        intermediate_results={"Zx_in3": 36.6},
        limit_states=[ls1],
        governing_limit_state=ls1,
        demand=300.0,
        capacity=500.0,
        dcr=0.60,
        status=CalculationStatus.PASS,
        reference_files=["database/aisc_360/v16th_ed/aisc_w_shapes.csv"],
        software_version="1.0.0"
    )


class TestProjectRepository:
    def test_create_and_get_project(self, temp_repo):
        prj = temp_repo.create_project(
            name="Hillside Residence",
            code="PRJ-HILL-01",
            client="Acme Builders",
            engineer="Jane Doe, PE",
            description="2-story custom residential home"
        )
        assert prj["name"] == "Hillside Residence"
        assert prj["code"] == "PRJ-HILL-01"
        assert prj["status"] == "ACTIVE"

        fetched = temp_repo.get_project(prj["project_id"])
        assert fetched is not None
        assert fetched["engineer"] == "Jane Doe, PE"

    def test_list_and_update_project(self, temp_repo):
        prj = temp_repo.create_project(name="Commercial Awning", code="PRJ-AWN-01")
        assert len(temp_repo.list_projects()) == 1

        updated = temp_repo.update_project(prj["project_id"], {"description": "Updated canopy"})
        assert updated is True
        fetched = temp_repo.get_project(prj["project_id"])
        assert fetched["description"] == "Updated canopy"

    def test_delete_project_cascade(self, temp_repo, sample_result):
        prj = temp_repo.create_project(name="To Delete", code="PRJ-DEL-01")
        calc = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="steel_beam",
            title="Beam Calc",
            code_edition="AISC 360-22",
            design_method=DesignMethod.ASD
        )
        temp_repo.save_calculation_run(calc["calculation_id"], sample_result)

        assert len(temp_repo.list_calculations_for_project(prj["project_id"])) == 1
        deleted = temp_repo.delete_project(prj["project_id"])
        assert deleted is True
        assert temp_repo.get_project(prj["project_id"]) is None
        assert temp_repo.get_calculation(calc["calculation_id"]) is None

    def test_revision_management(self, temp_repo, sample_result):
        prj = temp_repo.create_project(name="Parapet Design", code="PRJ-PAR-01")
        calc = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="cc_parapet",
            title="Parapet Wind Load",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.ASD
        )

        # Revision 1
        rev1 = temp_repo.save_calculation_run(
            calc["calculation_id"],
            sample_result,
            change_notes="Initial calc run",
            engineer="John Smith, PE"
        )
        assert rev1 == 1

        # Revision 2 with updated inputs and result
        sample_result.input_parameters["span_ft"] = 20.0
        sample_result.demand = 450.0
        sample_result.dcr = 0.90
        rev2 = temp_repo.save_calculation_run(
            calc["calculation_id"],
            sample_result,
            change_notes="Increased span to 20 ft",
            engineer="John Smith, PE"
        )
        assert rev2 == 2

        # Check revision history
        revisions = temp_repo.get_calculation_revisions(calc["calculation_id"])
        assert len(revisions) == 2
        assert revisions[0]["revision_number"] == 1
        assert revisions[1]["revision_number"] == 2

        # Verify revision 1 details preserved
        detail_rev1 = temp_repo.get_revision_detail(calc["calculation_id"], 1)
        assert detail_rev1["inputs"]["span_ft"] == 15.0
        assert detail_rev1["dcr"] == pytest.approx(0.60)

        # Verify revision 2 details
        detail_rev2 = temp_repo.get_revision_detail(calc["calculation_id"], 2)
        assert detail_rev2["inputs"]["span_ft"] == 20.0
        assert detail_rev2["dcr"] == pytest.approx(0.90)


class TestProjectAndHistoryServices:
    def test_project_service_workflow(self, temp_repo, sample_result):
        svc = ProjectService(repository=temp_repo)
        prj = svc.create_project(name="Active Project", engineer="Alice, PE")
        assert svc.active_project_id == prj["project_id"]

        calc = svc.create_calculation(
            module_id="cc_wind",
            title="Roof Overhang",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.LRFD
        )
        rev = svc.save_calculation_run(calc["calculation_id"], sample_result, change_notes="First run")
        assert rev == 1

        calcs = svc.list_calculations()
        assert len(calcs) == 1
        assert calcs[0]["calculation_id"] == calc["calculation_id"]

    def test_history_service_comparison(self, temp_repo, sample_result):
        prj_svc = ProjectService(repository=temp_repo)
        prj = prj_svc.create_project(name="Comparison Test")
        calc = prj_svc.create_calculation(
            module_id="steel_beam",
            title="Beam Check",
            code_edition="AISC 360-22",
            design_method=DesignMethod.ASD
        )

        # Rev 1
        sample_result.input_parameters["depth_in"] = 12.0
        sample_result.dcr = 0.75
        prj_svc.save_calculation_run(calc["calculation_id"], sample_result, "Baseline")

        # Rev 2
        sample_result.input_parameters["depth_in"] = 14.0
        sample_result.dcr = 0.55
        prj_svc.save_calculation_run(calc["calculation_id"], sample_result, "Increased beam depth")

        hist_svc = HistoryService(repository=temp_repo)
        diff = hist_svc.compare_revisions(calc["calculation_id"], 1, 2)

        assert diff["from_revision"] == 1
        assert diff["to_revision"] == 2
        assert "depth_in" in diff["input_diffs"]
        assert diff["input_diffs"]["depth_in"]["previous"] == 12.0
        assert diff["input_diffs"]["depth_in"]["current"] == 14.0
        assert diff["result_diffs"]["previous_dcr"] == pytest.approx(0.75)
        assert diff["result_diffs"]["current_dcr"] == pytest.approx(0.55)
        assert diff["result_diffs"]["dcr_delta"] == pytest.approx(-0.20)
