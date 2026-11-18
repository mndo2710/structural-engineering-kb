"""Unit tests for WP-2 contracts: ReferenceDataPort, restricted math markup, and structured trace."""

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Union

import pytest

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common import (
    AcceptanceCriterion,
    CalcStep,
    CalculationResult,
    CalculationStatus,
    CodeReference,
    DesignMethod,
    LimitStateResult,
    LoadPathStage,
    Quantity,
    RefSpec,
    is_valid_math_markup,
    math_markup_to_plain_text,
    math_markup_to_rich_html,
    validate_math_markup,
)
from core.ports import ReferenceDataPort


class _MinimalFakeReferenceData:
    """In-memory fake verifying ReferenceDataPort can be satisfied without pandas or app services."""

    def resolve_reference(self, identifier: str) -> Dict[str, Any]:
        return {"reference_id": identifier, "relative_path": "database/fake.csv"}

    def get_file_path(self, identifier: str) -> Path:
        return Path("database/fake.csv")

    def get_table(self, identifier: str) -> Any:
        return [{"col": 1}]

    def get_table_as_dicts(self, identifier: str) -> List[Dict[str, Any]]:
        return [{"col": 1}]

    def get_procedure(self, identifier: str) -> str:
        return "# Procedure"

    def lookup_value(self, identifier: str, match_col: str, match_val: Any, target_col: str) -> Any:
        return 42

    def filter_rows(self, identifier: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"col": 1}]

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        return "0" * 64

    def verify_integrity(self) -> Dict[str, Any]:
        return {"verified_count": 1, "missing_count": 0, "mismatch_count": 0}


class _IncompleteFake:
    def resolve_reference(self, identifier: str) -> Dict[str, Any]:
        return {}


class TestReferenceDataPort:
    def test_knowledge_base_service_satisfies_protocol(self):
        kb = KnowledgeBaseService()
        assert isinstance(kb, ReferenceDataPort)
        assert issubclass(KnowledgeBaseService, ReferenceDataPort)

    def test_minimal_fake_satisfies_protocol(self):
        fake = _MinimalFakeReferenceData()
        assert isinstance(fake, ReferenceDataPort)
        assert not isinstance(_IncompleteFake(), ReferenceDataPort)

    def test_ports_have_no_forbidden_imports(self):
        repo_root = Path(__file__).resolve().parent.parent
        port_files = [
            repo_root / "core" / "ports" / "__init__.py",
            repo_root / "core" / "ports" / "reference_data_port.py",
        ]
        forbidden_prefixes = ("app", "gui", "storage", "PySide6", "pandas")
        for path in port_files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith(forbidden_prefixes), (
                            f"Forbidden import '{alias.name}' in {path.name}"
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(forbidden_prefixes), (
                        f"Forbidden from-import '{node.module}' in {path.name}"
                    )


class TestMathMarkup:
    @pytest.mark.parametrize(
        "expr",
        [
            r"F_{e\parallel}",
            r"M_u \leq \phi M_n",
            r"M_u \le \phi M_n",
            r"\frac{R_n}{\Omega} \geq R_a",
            r"\frac{R_n}{\Omega} \ge R_a",
            r"t_{p,\text{req}} = \sqrt{\frac{4 M_{u,\text{plate}}}{0.90 F_y b_{\text{eff}}}}",
            r"\Delta_{\ell} = \left( \frac{P \cdot L^3}{3 E I} \right) \leq \frac{\ell}{240}",
            r"\left[ |(GC_p)_{wall}^+| + |(GC_p)_{roof}^-| \right]",
            r"K_{\theta} = 1 + 0.25 \cdot \left(\frac{\theta_{\max}}{90^\circ}\right)",
            r"V_n \neq 0 \pm \delta \approx \alpha + \beta - \gamma + \psi \cdot \mu / \rho",
            r"\sigma \cdot \tau \cdot \pi \cdot \epsilon \cdot \lambda \cdot \perp \cdot F_b^\prime",
            r"\mathrm{kip\text{-}in.} = \min(a, b) + \max(c, d) + \sum_{i=1}^{n} x_i",
            r"6100 lbs / 12.25 in.^2 = 498.0 psi <= 625.0 psi",
            r"0 < x and y > 1",
        ],
    )
    def test_valid_engineering_expressions(self, expr: str):
        assert is_valid_math_markup(expr) is True
        normalized = validate_math_markup(expr)
        assert isinstance(normalized, str) and len(normalized) > 0

    def test_whitespace_normalization(self):
        raw = "  M_u   \\leq \n\t  \\phi   M_n  "
        assert validate_math_markup(raw) == r"M_u \leq \phi M_n"

    @pytest.mark.parametrize(
        "bad_expr",
        [
            "",
            "   ",
            "<script>alert(1)</script>",
            "<div class='danger'>x</div>",
            "<img src=x onerror=alert(1)>",
            "<svg/onload=alert(1)>",
            r"\text{<script>}",
            "&ell;",
            r"F_{e} &times; 2",
            "&#123;",
            r"\text{&ell;}",
            r"F_{e\parallel",
            r"F_e}",
            r"\frac{a}{b",
            r"\sqrt{x",
            r"\left( a + b",
            r"a + b \right)",
            r"{\left( a} \right)",
            r"\left) a \right(",
            r"\input{/etc/passwd}",
            r"\include{secret}",
            r"\write18{whoami}",
            r"\def\foo{1}",
            r"\csname test\endcsname",
            r"\expandafter\foo",
            r"\catcode`\@=11",
            r"\url{https://example.com}",
            r"\href{https://example.com}{click}",
            "$$M_u = 10$$",
            "$M_u = 10$",
            r"\begin{aligned} a &= b \end{aligned}",
            r"\unknowncommand{x}",
            r"\mathrm{\input{bad}}",
            r"a \\ b",
            r"\frac{a}",
            r"\frac{}{b}",
            r"\sqrt{}",
            r"x_",
            r"x^",
            r"x_a_b",
            r"^2",
        ],
    )
    def test_invalid_or_dangerous_markup_rejected(self, bad_expr: str):
        assert is_valid_math_markup(bad_expr) is False
        with pytest.raises(ValueError):
            validate_math_markup(bad_expr)

    def test_math_markup_to_rich_html(self):
        assert math_markup_to_rich_html(r"F_{e\parallel}") == "F<sub>e∥</sub>"
        assert math_markup_to_rich_html(r"\phi R_n \geq R_u") == "φ R<sub>n</sub> ≥ R<sub>u</sub>"
        assert math_markup_to_rich_html(r"\frac{R_n}{\Omega} \geq R_a") == "R<sub>n</sub> / Ω ≥ R<sub>a</sub>"
        assert math_markup_to_rich_html(r"h_{par}^2") == "h<sub>par</sub><sup>2</sup>"
        assert math_markup_to_rich_html(r"45^\circ") == "45°"
        assert math_markup_to_rich_html(r"0 < x") == "0 &lt; x"

        ell_html = math_markup_to_rich_html(r"\Delta_{\ell} \leq \frac{\ell}{240}")
        assert ell_html == "Δ<sub>ℓ</sub> ≤ ℓ / 240"
        assert "&ell;" not in ell_html

    def test_math_markup_to_plain_text(self):
        assert math_markup_to_plain_text(r"F_{e\parallel}") == "F_e∥"
        assert math_markup_to_plain_text(r"a \cdot b \times c") == "a · b × c"
        assert math_markup_to_plain_text(r"\phi \cdot R_n \geq \Delta \cdot \theta") == "φ · R_n ≥ Δ · θ"
        assert math_markup_to_plain_text(r"\frac{R_n}{\Omega} \leq \ell") == "R_n / Ω ≤ ℓ"
        assert math_markup_to_plain_text(r"\sqrt{a^2 + b^2}") == "√(a^2 + b^2)"
        assert math_markup_to_plain_text(r"\sqrt[3]{a}") == "(a)^(1/3)"
        assert math_markup_to_plain_text(r"(a)^{1/2}") == "(a)^(1/2)"
        assert "&ell;" not in math_markup_to_plain_text(r"\ell")

    def test_converters_reject_invalid_markup(self):
        with pytest.raises(ValueError):
            math_markup_to_plain_text("<script>alert(1)</script>")
        with pytest.raises(ValueError):
            math_markup_to_rich_html("&ell;")


class TestStructuredTraceModels:
    def test_quantity_and_acceptance_round_trip(self):
        q = Quantity(symbol="  t_p  ", value=0.75, unit="in.", label="Base plate thickness")
        assert q.symbol == "t_p"
        assert Quantity.from_dict(q.to_dict()) == q

        with pytest.raises(ValueError):
            Quantity(symbol="   ", value=1.0)
        with pytest.raises(ValueError):
            Quantity(symbol="x", value=True)  # type: ignore[arg-type]

        acc_dcr = AcceptanceCriterion(
            comparison="<=",
            limit_value=1.0,
            limit_unit="",
            description="Demand-to-capacity ratio",
            is_dcr_check=True,
        )
        assert AcceptanceCriterion.from_dict(acc_dcr.to_dict()) == acc_dcr

        acc_non_dcr = AcceptanceCriterion(
            comparison="in_range",
            limit_value="0.50 to 2.00",
            limit_unit="",
            description="Aspect ratio applicability limit",
            is_dcr_check=False,
        )
        assert AcceptanceCriterion.from_dict(acc_non_dcr.to_dict()) == acc_non_dcr

        with pytest.raises(ValueError):
            AcceptanceCriterion(comparison="~=")

    def test_refspec_and_alias(self):
        assert CodeReference is RefSpec
        ref1 = RefSpec(
            code="AISC 360-22",
            edition="2022",
            kind="section",
            locator="Sec. J3.6",
            kb_reference_id="AISC360-22-Sec-J3",
            source_path="procedures/03_steel_design/steel_bolted_connection_aisc_workflow.md",
            sha256="a" * 64,
        )
        assert ref1.display_label == "AISC 360-22 Sec. J3.6"
        assert RefSpec.from_dict(ref1.to_dict()) == ref1

        ref2 = RefSpec(code="NDS", edition="2024", kind="table", locator="Table 12.3.3A")
        assert ref2.display_label == "NDS-2024 Table 12.3.3A"

        with pytest.raises(ValueError):
            RefSpec(code="", edition="2022", kind="section", locator="Sec. J3.6")
        with pytest.raises(ValueError):
            RefSpec(code="ASCE 7", edition="2022", kind="webpage", locator="Sec. 30.9")

    def test_calc_step_stages_non_dcr_and_multi_refs(self):
        ref_sec = RefSpec(code="NDS", edition="2024", kind="section", locator="Sec. 12.5.1")
        ref_tbl = RefSpec(
            code="NDS",
            edition="2024",
            kind="table",
            locator="Table 12.5.1A",
            kb_reference_id="NDS-2024-Table-12.5.1A",
        )
        step = CalcStep(
            step_id="S1",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Minimum End Distance Check",
            symbolic=r"e_{end} \geq a_{min} = 3.5 \cdot D",
            substituted=r"3.00 \text{ in.} \geq 2.19 \text{ in.}",
            variables={
                "e_end": Quantity("e_{end}", 3.0, "in.", "Provided end distance"),
                "D": Quantity("D", 0.625, "in.", "Bolt diameter"),
                "theta": 0.0,
            },
            result_value=3.0,
            result_unit="in.",
            acceptance=AcceptanceCriterion(
                comparison=">=",
                limit_value=2.19,
                limit_unit="in.",
                description="Minimum bolt end distance",
                is_dcr_check=False,
            ),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=[ref_sec, ref_tbl],  # list normalized to tuple
            note="Non-DCR geometric detailing check",
        )
        assert step.stage == 1
        assert isinstance(step.refs, tuple)
        assert len(step.refs) == 2
        assert step.dcr is None
        assert CalcStep.from_dict(step.to_dict()) == step

        # Reject out-of-range stages
        for bad_stage in (0, 5, True, "1"):
            with pytest.raises(ValueError):
                CalcStep(step_id="S_BAD", stage=bad_stage, title="Bad")  # type: ignore[arg-type]

        # Reject unsafe markup in symbolic or substituted
        with pytest.raises(ValueError):
            CalcStep(
                step_id="S_XSS",
                stage=2,
                title="Unsafe",
                symbolic="<script>alert(1)</script>",
            )
        with pytest.raises(ValueError):
            CalcStep(
                step_id="S_MAC",
                stage=2,
                title="Forbidden Macro",
                substituted=r"\input{evil.tex}",
            )


class TestCalculationResultSerialization:
    def test_round_trip_with_legacy_limit_states_and_trace(self):
        ls = LimitStateResult(
            step_id="LS1",
            name="Bolt Shear",
            code_clause="AISC 360-22 Sec. J3.6",
            equation_latex=r"\phi R_n = \phi \cdot F_{nv} \cdot A_b",
            substitution_str=r"0.75 \cdot 54.0 \text{ ksi} \cdot 0.442 \text{ in.}^2 = 17.9 \text{ kips}",
            demand=12.0,
            capacity=17.9,
            units="kips",
            dcr=0.67,
            status=CalculationStatus.PASS,
            notes="A325-N single shear",
        )
        assert LimitStateResult.from_dict(ls.to_dict()) == ls

        step1 = CalcStep(
            step_id="S1",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Bolt Edge Distance",
            symbolic=r"L_e \geq L_{e,\min}",
            substituted=r"1.50 \text{ in.} \geq 1.00 \text{ in.}",
            result_value=1.50,
            result_unit="in.",
            acceptance=AcceptanceCriterion(">=", 1.00, "in.", "AISC Table J3.4", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(RefSpec("AISC 360-22", "2022", "table", "Table J3.4"),),
        )
        step2 = CalcStep(
            step_id="S2",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Bolt Shear Strength",
            symbolic=r"\phi R_n = \phi \cdot F_{nv} \cdot A_b",
            substituted=r"0.75 \cdot 54.0 \cdot 0.442 = 17.9 \text{ kips}",
            variables={
                "phi": Quantity(r"\phi", 0.75, "", "Resistance factor"),
                "F_nv": Quantity("F_{nv}", 54.0, "ksi", "Nominal shear stress"),
                "A_b": Quantity("A_b", 0.442, "in.^2", "Nominal bolt area"),
            },
            result_value=17.9,
            result_unit="kips",
            acceptance=AcceptanceCriterion("<=", 1.0, "", "DCR <= 1.0", is_dcr_check=True),
            dcr=0.67,
            status=CalculationStatus.PASS,
            refs=(
                RefSpec("AISC 360-22", "2022", "section", "Sec. J3.6"),
                RefSpec("AISC 360-22", "2022", "equation", "Eq. J3-1"),
            ),
        )

        result = CalculationResult(
            calculation_id="calc-wp2-001",
            module_id="steel_bolt_connection",
            code_edition="AISC 360-22",
            design_method=DesignMethod.LRFD,
            input_parameters={"bolt_diameter_in": 0.75, "grade": "A325-N"},
            assumptions=["Threads included in shear plane (N)"],
            intermediate_results={"A_b_in2": 0.442},
            limit_states=[ls],
            governing_limit_state=ls,
            demand=12.0,
            capacity=17.9,
            dcr=0.67,
            status=CalculationStatus.PASS,
            reference_files=["database/aisc_360/v16th_ed/AISC360-22_Table_J3.2.csv"],
            software_version="1.0.0",
            warnings=[],
            trace=[step1, step2],  # list normalized to tuple
            is_stale=True,
            incomplete_reasons=["Example pending field"],
        )
        assert isinstance(result.trace, tuple)
        assert len(result.trace) == 2

        json_payload = json.dumps(result.to_dict())
        decoded = CalculationResult.from_dict(json.loads(json_payload))
        assert decoded == result
        assert decoded.trace[0].dcr is None
        assert decoded.trace[1].variables["F_nv"] == Quantity("F_{nv}", 54.0, "ksi", "Nominal shear stress")
        assert decoded.is_stale is True
        assert decoded.incomplete_reasons == ["Example pending field"]

    def test_backward_compatible_v1_payload_deserialization(self):
        legacy_payload = {
            "calculation_id": "calc-v1-legacy",
            "module_id": "asce7_parapet_wind",
            "code_edition": "ASCE 7-22",
            "design_method": "ASD",
            "demand": 150.0,
            "capacity": 300.0,
            "dcr": 0.50,
            "status": "PASS",
            "assumptions": ["Legacy assumption"],
            "intermediate_results": {"q_p_psf": 28.5},
            "limit_states": [
                {
                    "step_id": "S1",
                    "name": "Base Moment",
                    "code_clause": "ASCE 7-22 Sec. 30.9",
                    "equation_latex": "M_{base} = 0.5 \\cdot w \\cdot h^2",
                    "substitution_str": "150 lb-ft",
                    "demand": 150.0,
                    "capacity": 300.0,
                    "units": "lb-ft",
                    "dcr": 0.50,
                    "status": "PASS",
                    "notes": "",
                }
            ],
            "governing_limit_state": "Base Moment",
            "reference_files": [],
            "software_version": "1.0.0",
            "warnings": [],
        }
        restored = CalculationResult.from_dict(legacy_payload)
        assert restored.calculation_id == "calc-v1-legacy"
        assert restored.trace == ()
        assert restored.is_stale is False
        assert restored.incomplete_reasons == []
        assert restored.governing_limit_state is not None
        assert restored.governing_limit_state.step_id == "S1"

    def test_legacy_constructor_defaults(self):
        legacy = CalculationResult(
            calculation_id="calc-legacy-init",
            module_id="asce7_parapet_wind",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.ASD,
            input_parameters={"V_mph": 115.0},
        )
        assert legacy.trace == ()
        assert legacy.is_stale is False
        assert legacy.incomplete_reasons == []
        assert legacy.status == CalculationStatus.INCOMPLETE
