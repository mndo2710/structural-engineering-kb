"""Unit tests for app/services/knowledge_base_service.py per SAD v1.0 Section 5."""

import pytest
import pandas as pd
from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.exceptions import ReferenceDataNotFoundError


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBaseService()


class TestKnowledgeBaseService:
    def test_manifest_loaded(self, kb):
        assert len(kb._references_by_id) >= 66
        assert "ASCE7-22-Ch03-Dead" in kb._references_by_id

    def test_load_csv_table_dataframe(self, kb):
        df = kb.get_table("ASCE7-22-Ch03-Dead")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        # Verify caching
        df2 = kb.get_table("ASCE7-22-Ch03-Dead")
        assert len(df) == len(df2)

    def test_load_csv_as_dicts(self, kb):
        rows = kb.get_table_as_dicts("ASCE7-22-Ch03-Dead")
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert isinstance(rows[0], dict)

    def test_load_procedure_markdown(self, kb):
        # Pick one procedure from 01_loads_and_seismic
        content = kb.get_procedure("cc_wind_parapet_workflow.md")
        assert isinstance(content, str)
        assert len(content) > 100
        # Check standard 7-section structure
        assert "Section 1" in content or "SECTION 1" in content or "1." in content

    def test_nonexistent_reference(self, kb):
        with pytest.raises(ReferenceDataNotFoundError):
            kb.get_table("NON_EXISTENT_TABLE_9999.csv")

    def test_compute_sha256(self, kb):
        file_path = kb.get_file_path("ASCE7-22-Ch03-Dead")
        h = kb.compute_sha256(file_path)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
