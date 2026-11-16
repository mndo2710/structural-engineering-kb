# US Municipal Building Department Structural Plan Check Resolution Workflow & Standard Response Library (2024 IBC / 2025 CBC)

## 1. Governing Formatting & Engineering Resolution Rules (`@structural-plan-check`)
- **Direct Status Lead-In**: Start every formal response with `Addressed.` or `Acknowledged and coordinated.` followed immediately by the revised sheet number (`Sheet S0.01`, `Sheet S2.01`), calculation package section (`Structural Calculations, Page X`), and governing code clause.
- **Strict No-Numbering Rule**: Never use numbered lists (`1, 2, 3...`) inside plan check response blocks. Use concise prose paragraphs or hyphenated bullet points (`-`) with line breaks when separating drawing vs. calculation updates.
- **Complete Cross-Coordination**: Every response must reconcile structural plans, structural schedules (shear wall, holdown, post, and lintel schedules), architectural backgrounds, geotechnical report criteria, and calculation output sheets.

---

## 2. Module 1: General Notes, Expired Code/LARR Reports, Special Inspection & Geotechnical Coordination

### 2.1 Removal of Expired LARR / ICC-ES Evaluation Reports (City of Los Angeles / California Jurisdictions)
**Plan Check Comment Pattern**: *"General Notes list expired Los Angeles Research Reports (LARR) or discontinued evaluation programs (e.g., LARR program expired 06/25). Remove obsolete references and specify current ICC-ES Evaluation Reports (ESR) or City of LA Supplements."*
**Standard English Response**:
> Addressed. General Notes on Sheet S0.01 (Proprietary Connectors and Post-Installed Anchors section) have been revised to remove all expired LARR references and replace them with active ICC-ES Evaluation Reports with current City of Los Angeles Building Code Supplements (including ICC-ES ESR-3096 and ESR-3050 for Simpson Strong-Tie wood connectors, ESR-2502 for Titen HD screw anchors, and ESR-4057 for SET-3G epoxy adhesive anchors) in accordance with 2025 CBC Section 1704 and LADBS Information Bulletin P/BC 2023-092.

### 2.2 Geotechnical Report Parameters & Seismic Site Class Coordination (CBC Section 1803.6 / ASCE 7-22 Ch. 11)
**Plan Check Comment Pattern**: *"Coordinate Foundation Notes and seismic design parameters with the project Geotechnical Investigation Report (bearing capacity, passive pressure, friction coefficient, expansion index, and Site Class)."*
**Standard English Response**:
> Addressed. The Foundation Notes and Design Criteria block on Sheet S0.01 and the Seismic Design Parameters in the Structural Calculations (Section 1, Page 2) have been updated in strict accordance with the Geotechnical Engineering Report prepared by the Geotechnical Engineer of Record:
> - Allowable soil bearing pressure is specified as $q_{\text{allow}} = 1,500\text{ psf}$ for dead plus live loads (with a one-third increase permitted for transient wind or seismic loading per 2025 CBC Section 1806.1), equivalent fluid passive earth pressure is set to $300\text{ pcf/ft}$ (neglecting the top $1.0\text{ ft}$ of unconfined soil), and base friction coefficient is $\mu = 0.30$.
> - Seismic design parameters have been updated for Site Class D (Default) per ASCE 7-22 Section 11.4.3 and USGS Seismic Design Maps, and foundation detailing has been coordinated with the reported soil Expansion Index.

### 2.3 Statement of Special Inspections (2024 IBC / 2025 CBC Chapter 17)
**Plan Check Comment Pattern**: *"Provide complete Statement of Special Inspections on the structural plans for post-installed anchors, structural steel welding, high-strength bolting, masonry grouting, and wood shear wall nailing where fastening spacing is 4 inches on center or less."*
**Standard English Response**:
> Addressed. The Statement of Special Inspections schedule on Sheet S0.02 has been updated in accordance with 2025 CBC Sections 1704 and 1705 to explicitly include periodic/continuous special inspection for post-installed mechanical and epoxy anchors in concrete and CMU (per ICC-ES ESR-2502 and ESR-4057), structural welding per AWS D1.1/D1.4, masonry grout placement and prism verification per TMS 602, and wood shear wall/diaphragm nailing with edge fastener spacing of $4\text{ in.}$ o.c. or less per CBC Section 1705.12.2.

---

## 3. Module 2: Wind, Seismic, Orthogonal Load Combinations & Wall Out-of-Plane Anchorage (ASCE 7-22)

### 3.1 Redundancy Factor $\rho = 1.3$ & Orthogonal Seismic Load Combination (100% + 30%) (ASCE 7-22 Sec. 12.3.4 & 12.5.3)
**Plan Check Comment Pattern**: *"Justify redundancy factor $\rho = 1.0$ in Seismic Design Category D or re-analyze lateral system and collector/foundation elements using $\rho = 1.3$ and orthogonal 100% + 30% seismic load combinations."*
**Standard English Response**:
> Addressed. The lateral force-resisting system analysis and foundation overturning calculations in the Structural Calculations (Section 2) have been revised to apply a redundancy factor of $\rho = 1.3$ per ASCE 7-22 Section 12.3.4.2 and orthogonal seismic loading ($100\%$ of design seismic force in the primary direction combined with $30\%$ of design seismic force in the perpendicular direction per ASCE 7-22 Section 12.5.3.1) for all shared corner columns, intersecting shear wall boundary posts, and two-way footings.

### 3.2 Structural Wall Out-of-Plane Anchorage to Flexible Diaphragms (ASCE 7-22 Section 12.11.2)
**Plan Check Comment Pattern**: *"Provide calculations and continuous cross-tie detailing for out-of-plane wall anchorage of concrete/CMU walls to the wood roof diaphragm per ASCE 7-22 Section 12.11.2, including diaphragm flexibility factor $k_a$."*
**Standard English Response**:
> Addressed. Out-of-plane wall-to-diaphragm anchorage calculations have been added to the Structural Calculations per ASCE 7-22 Section 12.11.2.1 using $F_p = 0.4 S_{DS} k_a I_e W_p \ge 0.2 k_a I_e W_p$ with diaphragm amplification factor $k_a = 1.0 + L_f / 100$. Detail 4/S5.01 and Roof Framing Plan Sheet S2.02 have been updated to show Simpson Strong-Tie HDU/DTT2Z tension ties at $4\text{ ft}$ o.c. connected to sub-diaphragm rafters ($L/W \le 2.5:1$) and continuous steel strap cross-ties (`CMST14` / `CS16`) spanning from wall to wall across the building width, eliminating any cross-grain tension in the wood ledger per IBC Section 1604.8.3.

---

## 4. Module 3: Wood Framing, Shear Wall Reconciliation, Post Sizing & Holdown Schedule Cleanup (NDS 2024 / SDPWS 2021)

### 4.1 Shear Wall Length Discrepancies Between Plans and Calculations
**Plan Check Comment Pattern**: *"Shear wall lengths shown on the Framing Plans do not match the wall lengths used in the Structural Calculations. Reconcile all shear wall Pier IDs, lengths, and aspect ratios ($h/b_s \le 2.0\text{ or }3.5$)."*
**Standard English Response**:
> Addressed. All wood shear wall segment lengths, pier designations, and aspect ratios ($h / b_s$) have been reconciled between the Framing Plans (Sheet S2.01) and the Shear Wall Calculation Summary (Section 3) per AWC SDPWS 2021 Section 4.3.4. Where plan wall lengths were shorter than previously modeled, the calculation inputs have been updated to match the exact architectural plan dimensions, and where $2.0 < h / b_s \le 3.5$, the aspect ratio reduction factor $W_{ar} = 2 b_s / h$ per SDPWS Equation 4.3-2 has been applied to the unit shear capacity.

### 4.2 Mismatched Post Sizes & Removal of Unused Holdowns from Schedule
**Plan Check Comment Pattern**: *"Boundary post sizes at shear wall ends do not match between plans, holdown schedule, and calculations, and the Holdown Schedule lists holdown types not called out on the framing plans. Coordinate and remove unused schedule entries."*
**Standard English Response**:
> Addressed. Boundary post callouts on Framing Plan Sheet S2.01, Foundation Plan Sheet S1.01, the Holdown Schedule on Sheet S0.02, and the shear wall overturning calculations have been fully coordinated:
> - All shear wall boundary posts have been updated to match the minimum post thickness and width required for the specified Simpson Strong-Tie HDU holdowns and `SDS` screw penetration per ICC-ES ESR-2330, and verified for combined axial compression and bearing on the sill plate per NDS 2024 Sections 3.6 and 3.10.
> - Unused holdown models not referenced on the structural framing or foundation plans have been removed from the Holdown Schedule on Sheet S0.02.

---

## 5. Module 4: Structural Steel Connections, HSS Wall Plastification & Base Plates (AISC 360-22)

### 5.1 HSS-to-HSS Moment/Shear Connection Local Sidewall Checks (AISC 360 Chapter K)
**Plan Check Comment Pattern**: *"For HSS beam-to-HSS column connections, provide local limit state checks for the supporting HSS column wall (chord wall plastification, punching shear, sidewall yielding, and sidewall crippling per AISC 360 Chapter K)."*
**Standard English Response**:
> Addressed. Complete AISC 360-22 Chapter K local connection calculations have been added to the Structural Calculations (Section 4) using the design wall thickness $t_{\text{des}} = 0.93 t_{\text{nom}}$ per AISC 360 Section B4.2. The supporting HSS column has been verified for uneven load distribution (Sec. K4.2, Eq. K4-6), chord wall plastification under in-plane bending (Table K4.2, Eq. K4-2), punching shear (Eq. K4-7), and local sidewall yielding/crippling (Eqs. K4-3 and K4-4). Where width ratio $\beta < 0.85$ governed chord face plastification, $3/8\text{ in.}$ top and bottom continuity/diaphragm plates have been added to Detail 6/S5.02.

---

## 6. Module 5: Concrete & CMU Anchorage, Out-of-Plane Breakout & Confining Hairpins (ACI 318-19 Ch. 17 & TMS 402-22)

### 6.1 Out-of-Plane Breakout & Confining Hairpin Reinforcement for Embedded Posts / Close-Edge Anchors
**Plan Check Comment Pattern**: *"For steel posts embedded in CMU/concrete walls or base plates near slab edges, longitudinal development alone does not prevent out-of-plane face-shell spalling or concrete edge breakout. Provide out-of-plane breakout check per ACI 318 Ch. 17 / TMS 402 Sec. 8.1.3 or detail confining anchor hairpins."*
**Standard English Response**:
> Addressed. Out-of-plane masonry/concrete breakout and one-way bond beam shear checks have been added to the Structural Calculations per TMS 402-22 Sections 8.1.3.2 and 8.3.5.1.2 and ACI 318-19 Sections 17.6.2 and 17.7.2, neglecting the top $1.5\text{ in.}$ unconfined cover zone ($a_0$). In addition, Detail 3/S5.03 has been revised to provide $\text{#4}$ U-bar anchor reinforcement hairpins at the top bearing zone and bottom reaction zone, physically hooking around and enclosing the adjacent vertical jamb reinforcement outside the $45^\circ$ breakout cone in accordance with ACI 318-19 Section 17.5.2.1(b) and ACI 315 Section 2.8.3.

---

## 7. Module 6: Components & Cladding Sub-Assemblies (Guardrails, Trellises & Awnings)

### 7.1 Deck Guardrail Post-to-Framing Connection (Eliminating Notched Posts & Cross-Grain Tension)
**Plan Check Comment Pattern**: *"Show calculations and details for deck guardrail post attachment for a 200 lb concentrated load at the top rail per IBC Section 1607.9.1.1 without notching 4x4 posts or inducing cross-grain tension in the wood rim joist."*
**Standard English Response**:
> Addressed. Guardrail post and connection calculations have been added to the Structural Calculations per 2024 IBC Section 1607.9.1.1 and ASCE 7-22 Section 4.5.1 for a $200\text{ lb}$ concentrated load applied at the top of the $42\text{ in.}$ guard. Detail 8/S5.01 specifies a full un-notched $4\times 4$ DF-L #1 post connected with an upper Simpson Strong-Tie `DTT2Z` tension tie anchored directly into the perpendicular deck joist/full-depth blocking and a lower $1/2\text{ in.}$ through-bolt bearing against solid blocking, resolving the overturning moment couple ($T = M / d_{\text{couple}}$) without inducing cross-grain tension in the rim joist per NDS Section 11.1.2.
