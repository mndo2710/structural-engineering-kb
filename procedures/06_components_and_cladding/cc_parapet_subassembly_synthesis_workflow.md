# End-to-End Calculation Procedure: Roof Parapet Sub-Assembly Synthesis (Wood Stud, Structural Steel HSS, & Reinforced CMU/Concrete)

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Structural Sub-Assembly**: Unbraced cantilevered or diagonally braced roof parapet extending a height $h_p$ above the roof diaphragm level ($z = h$), constructed of:
  - **System A (Wood Stud Parapet)**: Continuous balloon-framed wood studs ($2\times 6$ or $2\times 8$ DF-L #2 at spacing $s \in \{12, 16, 24\}\text{ in.}$ o.c.) extending from the story below past the roof framing, or platform-framed parapet studs anchored via Simpson Strong-Tie straps/holdowns ([Simpson C-C-2026 Catalog](https://www.strongtie.com/)).
  - **System B (Structural Steel HSS Post Parapet)**: Cantilevered square/rectangular hollow structural sections ($\text{HSS}4\times 4\times 1/4$, ASTM A500 Grade C) welded to a base plate anchored to a concrete roof slab/beam or bolted to steel roof framing ([SkyCiv Steel Design Documentation](https://skyciv.com/docs/)).
  - **System C (Reinforced Concrete or CMU Masonry Parapet)**: Cantilevered reinforced masonry ($8\text{ in.}$ CMU, $f'_m = 2,000\text{ psi}$) or reinforced concrete wall extending above the roof bond beam / diaphragm chord ([ENERCALC ASCE 7-22 Wall Anchorage](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)).

### 1.2 Governing Codes & Standards
- **Building Code**: [2024 International Building Code (IBC) / 2025 California Building Code (CBC) Chapter 16](https://codes.iccsafe.org/content/WABellevueBC2021P1/chapter-16-structural-design)
- **Wind & Seismic Loads**: [ASCE/SEI 7-22 Section 30.9 (Parapets Wind), Section 13.3.1 & Table 13.5-1 (Parapet Seismic), and Section 12.11.2 (Structural Wall Out-of-Plane Anchorage)](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)
- **Material Standards**: AWC NDS 2024 & SDPWS 2021 (Wood), ANSI/AISC 360-22 (Structural Steel), ACI 318-19/25 & TMS 402/602-22 (Concrete & Masonry)
- **Required Repository Database Tables**:
  - `database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv`, `ASCE7-22_Table_26.10-1.csv`, `ASCE7-22_Table_C30.3-1.csv`
  - `database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv`
  - `database/asce_7/v7_22/ASCE7-22_Section_12.11.2_Wall_Anchorage_and_Table_13.6-1_Equipment.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`

### 1.3 Complete Load Path & Force Transfer Mechanism
1. **Cantilever Parapet Exposure ($z > h$)**: Out-of-plane wind pressure ($p_p$) or seismic inertia force ($F_{p,\text{parapet}}$) acts normal to the parapet surface over cantilever height $h_p$.
2. **Base Fixity at Roof Diaphragm Level ($z = h$)**: At the roof diaphragm intersection, the parapet develops maximum cantilever bending moment $M_{\text{base}}$ and horizontal base shear $V_{\text{base}}$.
3. **Diaphragm Collector / Wall Anchorage ($F_{p,\text{anch}}$)**: The roof diaphragm resists the horizontal reaction from the parapet PLUS the tributary top half of the story wall below ($h_{\text{wall}}/2$) per [ASCE 7-22 Section 12.11.2](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2).
4. **Moment Couple Resolution into Supporting Roof Framing**: For platform-framed wood or steel post parapets not continuous with the wall studs below, the cantilever overturning moment $M_{\text{base}}$ resolves into a horizontal tension/compression couple at the top and bottom of the roof joist/rafter depth ($T_c = C_c = M_{\text{base}} / d_{\text{joist}}$) or vertical holdown uplift couple ($R_{\text{roof}} = M_{\text{base}} / L_{\text{backspan}}$).

---

## Section 2: Load Combinations & Internal Forces at the Critical Section

### 2.1 Component & Cladding Wind Pressure on Parapet (ASCE 7-22 Section 30.9)
Per ASCE 7-22 Eq. 30.9-1, the design wind pressure on the parapet is:
$$p_p = q_p \cdot (GC_{pn}) \quad (\text{psf})$$
where:
- $q_p = 0.00256 K_{zp} K_{zt} K_d K_e V^2$ = velocity pressure evaluated at the top of the parapet ($z_p = h + h_p$), with $K_d = 0.85$.
- $GC_{pn} = +1.5$ for **Windward Parapet** (combines positive windward front wall pressure + negative leeward back surface suction).
- $GC_{pn} = -1.0$ for **Leeward Parapet** (combines negative windward roof suction + negative leeward exterior wall suction).
- **Separate Cladding Check**: Sheathing and fasteners on each face of the parapet are checked for individual wall/roof zone pressures ($GC_p - GC_{pi}$) from `ASCE7-22_Table_C30.3-1.csv`.

Unfactored wind shear and overturning moment per unit length (or per post spacing $S$) at the roof line:
$$V_{W,\text{base}} = p_p \cdot h_p \cdot S \quad (\text{lbs}), \qquad M_{W,\text{base}} = \frac{p_p \cdot h_p^2 \cdot S}{2} \quad (\text{lb-ft})$$

### 2.2 Nonstructural Cantilever Seismic Force on Parapet (ASCE 7-22 Section 13.3.1 & Table 13.5-1)
From `ASCE7-22_Table_13.5-1.csv` for unbraced cantilever parapets supported above grade: $C_{AR} = 2.2$, $R_{po} = 1.5$, $\Omega_{0p} = 1.75$, and $I_p = 1.0$ (or $1.5$ for Risk Category IV):
$$F_{p,\text{parapet}} = 0.4 S_{DS} I_p W_p \left(\frac{H_f}{R_\mu}\right) \left(\frac{C_{AR}}{R_{po}}\right)$$
At the roof level ($z = h$), if building period $T_a$ is unknown, $H_f = 1 + 2.5(z/h) = 3.5$ per [ASCE 7-22 Eq. 13.3-5](https://seblog.strongtie.com/2026/05/asce-7-22-shakes-things-up-changes-to-seismic-calculations-for-anchorage-of-equipment/), subject to:
$$0.3 S_{DS} I_p W_p \le F_{p,\text{parapet}} \le 1.6 S_{DS} I_p W_p$$
Unfactored seismic shear and overturning moment at the roof line (with parapet weight $W_p = w_p \cdot h_p \cdot S$ acting at $h_p / 2$):
$$V_{E,\text{base}} = F_{p,\text{parapet}} \quad (\text{lbs}), \qquad M_{E,\text{base}} = F_{p,\text{parapet}} \cdot \left(\frac{h_p}{2}\right) \quad (\text{lb-ft})$$

### 2.3 Governing Factored Demands (LRFD & ASD per ASCE 7-22 Chapter 2)
- **LRFD**:
  $$V_u = \max(1.0 V_{W,\text{base}},\; 1.0 V_{E,\text{base}}), \qquad M_u = \max(1.0 M_{W,\text{base}},\; 1.0 M_{E,\text{base}})$$
  *(For concrete/masonry anchorage, apply overstrength $\Omega_{0p} = 1.75$ to seismic demands: $V_{u,\Omega} = 1.75 V_{E,\text{base}},\; M_{u,\Omega} = 1.75 M_{E,\text{base}}$).*
- **ASD**:
  $$V_a = \max(0.6 V_{W,\text{base}},\; 0.7 V_{E,\text{base}}), \qquad M_a = \max(0.6 M_{W,\text{base}},\; 0.7 M_{E,\text{base}})$$

---

## Section 3: Primary Member Verification at the Roof Line Interface

### 3.1 System A: Wood Stud Parapet Check (AWC NDS 2024 Chapter 3)
For balloon-framed wood studs of width $b$ and depth $d$ ($S_x = b d^2 / 6$, $A = b d$) with load duration factor $C_D = 1.60$ (wind/seismic) and repetitive member factor $C_r = 1.15$:
1. **Flexural Stress Check (NDS Sec. 3.3.1)**:
   $$f_b = \frac{12 M_a}{S_x} \le F'_b = F_b C_D C_M C_t C_L C_F C_r \quad (\text{psi})$$
2. **Horizontal Shear Stress Check (NDS Sec. 3.4.1)**:
   $$f_v = \frac{1.5 V_a}{b \cdot d} \le F'_v = F_v C_D C_M C_t \quad (\text{psi})$$
3. **Cantilever Top Deflection Check (IBC Table 1604.3)**:
   Using service wind load $0.6 W$ (or $0.42 W$ per IBC Table 1604.3 Footnote f) and $I_x = b d^3 / 12$, taking cantilever span as $2 h_p$:
   $$\Delta_{\text{top}} = \frac{(0.6 w_W) (12 h_p)^4}{8 E' I_x} \le \frac{2 (12 h_p)}{120} = \frac{h_p}{5}\text{ (in.)}$$

### 3.2 System B: Structural Steel HSS Post Check (AISC 360-22 Chapters F & G)
For cantilevered square HSS post ($F_y = 50\text{ ksi}$) with design wall thickness $t_{\text{des}} = 0.93 t_{\text{nom}}$ ([AISC 360 Sec. B4.2](https://skyciv.com/docs/)):
1. **Flexural Yielding Capacity (AISC Sec. F7.1, Compact Box)**:
   $$M_n = M_p = F_y Z_x, \qquad \phi_b M_n = 0.90 M_p \ge M_u \quad \text{(LRFD)}, \qquad \frac{M_n}{\Omega_b} = \frac{M_p}{1.67} \ge M_a \quad \text{(ASD)}$$
2. **Web Shear Capacity (AISC Sec. G4)**:
   $$V_n = 0.6 F_y A_w C_{v2} = 0.6 F_y (2 h t_{\text{des}}) (1.0), \qquad \phi_v V_n = 0.90 V_n \ge V_u, \qquad \frac{V_n}{\Omega_v} = \frac{V_n}{1.67} \ge V_a$$

### 3.3 System C: Reinforced CMU / Concrete Parapet Check (TMS 402-22 Ch. 8/9 or ACI 318-19)
For reinforced CMU parapet with vertical bars $A_s$ at spacing $s$ placed at effective depth $d$ (Typically centered in 8 in. CMU: $d = 3.81\text{ in.}$):
- **ASD Cracked Elastic Flexure (TMS 402 Sec. 8.3.4.2)**:
  $$f_b = \frac{M_a}{\frac{1}{2} k j b d^2} \le F_b = 0.45 f'_m, \qquad f_s = \frac{M_a}{A_s j d} \le F_s = 32,000\text{ psi}$$
- **LRFD Nominal Flexural Strength (TMS 402 Sec. 9.3.4.1.2)**:
  $$\phi M_n = 0.90 A_s f_y \left(d - \frac{a}{2}\right) \ge M_u, \qquad a = \frac{A_s f_y}{0.80 f'_m b}$$

---

## Section 4: Sequential Connection Limit States Along the Load Path

### Step 4.1: Roof-to-Wall Out-of-Plane Anchorage Force ($F_{p,\text{anch}}$ per ASCE 7-22 Section 12.11.2)
Query `ASCE7-22_Section_12.11.2_Wall_Anchorage_and_Table_13.6-1_Equipment.csv` ([ENERCALC ASCE 7-22 Wall Anchorage](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)):
1. **Flexible Diaphragm Amplification Factor ($k_a$)**:
   $$k_a = 1.0 + \frac{L_f}{100} \quad \text{with} \quad 1.0 \le k_a \le 2.0$$
   where $L_f$ is the span (ft) of the flexible wood/steel-deck roof diaphragm providing lateral support (for rigid concrete diaphragms, $k_a = 1.0$).
2. **Unit Out-of-Plane Wall Anchorage Pressure ($p_{\text{anch}}$ at $z = h$)**:
   $$p_{\text{anch}} = \max\left(0.4 S_{DS} k_a I_e w_{\text{wall}},\; 0.2 k_a I_e w_{\text{wall}},\; 5.0\text{ psf}\right)$$
3. **Total Out-of-Plane Tension/Compression Reaction at Roof Diaphragm Line**:
   By static equilibrium of the continuous wall-parapet beam at the roof support (or tributary height $h_{\text{trib}} = \frac{h_{\text{story}}}{2} + h_p$):
   $$R_{\text{diaphragm}} = V_{\text{base,parapet}} + \frac{M_{\text{base,parapet}}}{h_{\text{story}}} + p_{\text{anch}} \cdot \left(\frac{h_{\text{story}}}{2}\right) \cdot S$$

### Step 4.2: Platform-Framed Parapet Moment Transfer into Roof Framing
When parapet studs or steel posts terminate at the roof framing rather than extending continuously as balloon studs:
1. **Horizontal Strap / Blocking Force Couple Across Roof Joist Depth ($d_{\text{joist}}$)**:
   $$T_{\text{top}} = C_{\text{bot}} = \frac{M_{\text{base}}}{d_{\text{joist}}} + \frac{V_{\text{base}}}{2}$$
   Select a Simpson Strong-Tie strap (`LSTA`, `MSTA`, `CS16`, or `CMST14` from `Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv`) over the top of the roof blocking/rafter and solid blocking at the bottom plate such that:
   $$T_{\text{allow,strap}} \ge T_{\text{top,ASD}}$$
2. **Vertical Holdown / Overturning Couple on Cantilever Post Base**:
   If a Simpson holdown (`HDU2-SDS2.5` or `DTT2Z` from `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`) is mounted on the parapet post with lever arm $d_h$:
   $$T_{\text{holdown}} = \frac{M_{\text{base}}}{d_h} \le T_{\text{allow,HDU}}$$

### Step 4.3: Concrete / Masonry Wall-to-Diaphragm Tension Tie (DTT2Z / HDU / Embedded PAB)
Per [ASCE 7-22 Section 12.11.2.2.5](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2) and IBC Section 1604.8.3, wood ledgers **shall never be loaded in cross-grain bending or cross-grain tension**.
- Provide positive direct tension ties ([Simpson DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2) or `HDU` holdowns anchored directly into the roof rafters/sub-diaphragm blocking and into the CMU bond beam / concrete wall via `SET-3G` epoxy or cast-in `PAB` anchors):
  $$T_{u,\text{anchor}} = R_{\text{diaphragm,LRFD}} \le \phi N_{\text{anchor}} \quad (\text{ACI 318-19 Ch. 17 / TMS 402 Sec. 8.1.3})$$

---

## Section 5: Supporting Member / Global Roof Framing Verification

### 5.1 Roof Rafter / Joist Added Bending from Parapet Overturning ($M_{\text{base}}$)
When a non-balloon parapet transfers base moment $M_{\text{base}}$ into a roof rafter or truss spanning $L_{\text{rafter}}$:
- **Vertical Reaction Induced on Supporting Wall and Interior Support**:
  $$\Delta R_{\text{rafter}} = \pm \frac{M_{\text{base}}}{L_{\text{rafter}}}$$
- **Superimposed Bending Stress in Roof Rafter**:
  Verify that the roof rafter satisfies combined gravity + wind/seismic bending and axial collector tension/compression (NDS 2024 Sec. 3.9):
  $$\frac{f_t}{F'_t} + \frac{f_{b,\text{gravity}} + f_{b,\text{parapet}}}{F^*_b} \le 1.0$$

### 5.2 Sub-Diaphragm & Continuous Crosstie Verification (ASCE 7-22 Section 12.11.2.2)
- Sub-diaphragm aspect ratio shall satisfy $L_{\text{sub}} / W_{\text{sub}} \le 2.5 : 1.0$ ([SDPWS 2021 Sec. 4.2.5](https://www.strongtie.com/)).
- Continuous ties across the full building width between main diaphragm chords must resist the sub-diaphragm reaction force.

---

## Section 6: Mandatory Detailing & Construction Notes
- **Balloon Framing Preference (Wood Parapets)**: Where architectural geometry permits, extend exterior wall studs continuously past the roof ledger/blocking to form the parapet (balloon framing) to eliminate discontinuous moment splices at the roof line.
- **Cross-Grain Tension Prohibition**: Per IBC Section 1604.8.3 and ASCE 7-22 Section 12.11.2.2.5, wood ledgers shall only resist vertical shear and parallel-to-grain forces; all out-of-plane wall/parapet anchorage forces ($F_p$) shall be transferred directly into roof framing via approved tension ties (`DTT2Z`, `HDU`, or `PAB`).
- **Continuous Rim Blocking & Strapping**: Provide full-depth solid blocking between roof joists at all parapet post/stud locations; install all specified Simpson Strong-Tie `10d`/`16d` nails or `SDS` screws into wide faces of framing members.
- **Flashing & Moisture Protection**: All wood parapet framing and connectors exposed to weather or beneath parapet coping shall use preservative-treated lumber or ZMAX / Stainless Steel (`SS`) hardware per Simpson Strong-Tie Corrosion Guidelines.

---

## Section 7: Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :--- | :--- | :--- | :--- |
| **1** | Parapet Wind Pressure ($p_p$) | ASCE 7-22, Sec. 30.9 (Eq. 30.9-1) | $p_p = q_p (GC_{pn})$ with $GC_{pn} = +1.5$ (windward), $-1.0$ (leeward) |
| **2** | Parapet Seismic Force ($F_{p,\text{parapet}}$) | ASCE 7-22, Sec. 13.3.1 & Table 13.5-1 | $F_p = 0.4 S_{DS} I_p W_p (H_f / R_\mu)(C_{AR} / R_{po})$ ($C_{AR}=2.2, R_{po}=1.5$) |
| **3.1** | Parapet Stud / Post Flexure & Shear | NDS 2024 Ch. 3 / AISC 360 Ch. F–G / TMS 402 | $f_b \le F'_b,\; f_v \le F'_v$ (ASD) or $M_u \le \phi M_n,\; V_u \le \phi V_n$ (LRFD) |
| **3.2** | Parapet Top Deflection | 2024 IBC, Table 1604.3 | $\Delta_{\text{top}} \le (2 h_p) / 120 = h_p / 60$ |
| **4.1** | Out-of-Plane Wall Anchorage ($F_{p,\text{anch}}$) | ASCE 7-22, Sec. 12.11.2.1 | $F_p = \max(0.4 S_{DS} k_a I_e W_p,\; 0.2 k_a I_e W_p,\; 5\text{ psf} \cdot A_{\text{trib}})$ |
| **4.2** | Base Moment Force Couple ($T_c, C_c$) | Equilibrium & Simpson C-C-2026 | $T_{\text{top}} = M_{\text{base}} / d_{\text{joist}} \le T_{\text{allow,strap}}$ |
| **4.3** | Wall-to-Diaphragm Positive Tension Tie | IBC Sec. 1604.8.3 & ACI 318 Ch. 17 | $T_{\text{tie}} \le T_{\text{allow,DTT2Z/HDU}}$ (Zero cross-grain tension in ledger) |
| **5** | Supporting Roof Rafter & Sub-Diaphragm | NDS Sec. 3.9 & SDPWS Sec. 4.2.5 | $\frac{f_t}{F'_t} + \frac{f_b}{F^*_b} \le 1.0$; Sub-diaphragm $L / W \le 2.5 : 1$ |
