# US Structural Engineering Knowledge Base & Calculation Architecture (`structural-engineering-kb`)

Standardized US Structural Engineering Code Lookup Databases (`.csv`), Step-by-Step Plan Check Calculation Procedures (`.md`), and Automated Desktop Application Architecture (`core/`, `exporters/`, `gui/`, `tests/`) in US Customary Units (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-ft`, `kip-ft`) supporting parallel **ASD** and **LRFD** design philosophies.

---

## 1. Active Building Codes & Reference Standards
- **Building Code**: [2024 International Building Code (IBC) / 2025 California Building Code (CBC)](https://codes.iccsafe.org/content/WABellevueBC2021P1/chapter-16-structural-design)
- **Minimum Design Loads**: [ASCE/SEI 7-22 (Minimum Design Loads and Associated Criteria for Buildings and Other Structures)](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)
- **Structural Wood & Lateral Design**: AWC NDS 2024 (*National Design Specification for Wood Construction*) & AWC SDPWS 2021 (*Special Design Provisions for Wind and Seismic*)
- **Structural Steel Design**: [ANSI/AISC 360-22, AISC 341-22, AISC Steel Construction Manual (16th Ed.), & AISC Design Guide 1 / 24](https://skyciv.com/docs/)
- **Concrete & Masonry Design**: [ACI 318-19 / 318-25 (Building Code Requirements for Structural Concrete, Chapter 17 Anchorage)](https://www.steelsolver.com/p/anchor-bolt-tension-calculator.html) & [TMS 402/602-22 (Building Code Requirements for Masonry Structures)](https://www.scribd.com/document/450073931/Anchor-pdf)
- **Proprietary Connectors & Anchors**: [Simpson Strong-Tie Wood Construction Connectors (C-C-2026) & Anchoring Systems (C-A-2023)](https://www.strongtie.com/)

---

## 2. Repository Directory Structure & 10-Day Completed Inventory

```text
structural-engineering-kb/
├── config/
│   ├── active_code_registry.json
│   └── app_settings.json
├── database/
│   ├── asce_7/v7_22/
│   │   ├── ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv
│   │   ├── ASCE7-22_Table_13.5-1.csv
│   │   ├── ASCE7-22_Section_12.11.2_Wall_Anchorage_and_Table_13.6-1_Equipment.csv
│   │   ├── ASCE7-22_Table_26.6-1.csv
│   │   ├── ASCE7-22_Table_26.9-1.csv
│   │   ├── ASCE7-22_Table_26.10-1.csv
│   │   ├── ASCE7-22_Table_26.13-1.csv
│   │   ├── ASCE7-22_Figure_29.4-2.csv
│   │   ├── ASCE7-22_Table_C30.3-1.csv
│   │   ├── ASCE7-22_Table_C30.3-2_C30.3-3.csv
│   │   └── ASCE7-22_Figure_30.11-1A_1B.csv
│   ├── ibc_cbc/v2024_ibc_v2025_cbc/
│   │   └── IBC-2024_Section_1607.9_Guardrail_Loads.csv
│   ├── nds_wood/v2024/
│   │   ├── NDS-2024_Table_11.3.1_Adjustment_Factors.csv
│   │   ├── NDS-2024_Table_12.3.3_Dowel_Bearing_Strength_Fe.csv
│   │   ├── NDS-2024_Table_12.5.1A_to_12.5.1G_Bolt_LagScrew_Geometry.csv
│   │   ├── NDS-2024_Table_12E_Bolts_Single_Shear.csv
│   │   ├── NDS-2024_Table_12J_12K_Lag_Screws.csv
│   │   ├── NDS-2024_Table_12L_12M_Wood_Screws_and_Nails.csv
│   │   ├── NDS-2024_Appendix_E_Group_Action_and_Tear_Out.csv
│   │   ├── NDS-2024_Appendix_L1_L7_L8_Fastener_Dimensions_and_Washers.csv
│   │   └── sdpws/
│   │       ├── SDPWS-2021_Table_4.2A_Blocked_Diaphragms.csv
│   │       ├── SDPWS-2021_Table_4.2C_Unblocked_Diaphragms.csv
│   │       └── SDPWS-2021_Table_4.3A_Shear_Walls.csv
│   ├── aisc_360/ch_j_connections/
│   │   ├── AISC360-22_Table_J2.4.csv
│   │   ├── AISC360-22_Table_J2.5_Welded_Joints.csv
│   │   ├── AISC360-22_Table_J3.2_Bolt_Strength.csv
│   │   ├── AISC360-22_Table_J3.3_J3.4_J3.5_Bolt_Holes_and_Edge_Distances.csv
│   │   ├── AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv
│   │   ├── AISC_Manual_16th_Part10_Shear_Tab_and_Single_Angle_Design.csv
│   │   ├── AISC360-22_Table_K3.2_K4.2_HSS_Connections.csv
│   │   └── AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv
│   ├── aci_318_tms_402/
│   │   ├── aci_318_19/
│   │   │   ├── ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv
│   │   │   └── ASTM_F1554_and_Headed_Anchor_Bolt_Properties.csv
│   │   └── tms_402_22/
│   │       └── TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv
│   └── manufacturer_catalogs/simpson_strong_tie/
│       ├── Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv
│       ├── Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv
│       ├── Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv
│       ├── Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv
│       ├── Simpson_C-C-2026_Post_Bases_and_Caps_ABU_ABA_CBSQ_MPBZ_CC_BC.csv
│       └── Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv
├── procedures/
│   ├── 01_loads_and_seismic/
│   │   ├── cc_wind_parapet_workflow.md
│   │   ├── cc_wind_overhang_workflow.md
│   │   ├── cc_awning_canopy_loads_workflow.md
│   │   ├── open_trellis_wind_seismic_workflow.md
│   │   └── guardrail_handrail_loads_ibc_workflow.md
│   ├── 02_wood_design/
│   │   ├── wood_nail_screw_connection_nds_workflow.md
│   │   ├── wood_lag_screw_sds_connection_nds_workflow.md
│   │   ├── wood_bolted_connection_tearout_nds_workflow.md
│   │   ├── wood_diaphragm_chord_collector_sdpws_workflow.md
│   │   ├── wood_shear_wall_holdown_sdpws_workflow.md
│   │   └── wood_joist_hanger_hurricane_tie_simpson_workflow.md
│   ├── 03_steel_design/
│   │   ├── steel_bolted_connection_aisc_workflow.md
│   │   ├── steel_welded_connection_aisc_workflow.md
│   │   ├── steel_column_base_plate_aisc_dg1_workflow.md
│   │   ├── steel_shear_tab_connection_aisc_workflow.md
│   │   ├── steel_single_double_angle_shear_aisc_workflow.md
│   │   └── steel_hss_to_hss_moment_shear_aisc_workflow.md
│   ├── 04_concrete_masonry_foundation/
│   │   ├── concrete_anchorage_aci318_ch17_workflow.md
│   │   ├── cmu_masonry_anchorage_out_of_plane_breakout_tms402_workflow.md
│   │   └── cantilever_steel_post_embedded_concrete_cmu_workflow.md
│   ├── 05_plan_check_responses/
│   │   ├── standard_plan_check_responses.md
│   │   └── plan_check_response_master_workflow_and_templates.md
│   └── 06_components_and_cladding/
│       ├── cc_parapet_subassembly_synthesis_workflow.md
│       ├── cc_cantilever_tieback_awning_subassembly_workflow.md
│       ├── cc_wood_steel_trellis_patio_subassembly_workflow.md
│       └── cc_deck_guardrail_post_subassembly_workflow.md
├── core/               # Python calculation engines (asce7, aisc360, nds, aci318)
├── exporters/          # Standardized 17-column Arial 10pt openpyxl builder & Source_Audit logger
├── gui/                # CustomTkinter desktop UI
├── tests/              # Automated unit verification against benchmark workbooks
├── main.py             # Application entry point
└── state_summary.txt   # Rolling project state & Google Drive File ID registry
```
