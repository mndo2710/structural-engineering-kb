# End-to-End Calculation Procedure: Attached & Freestanding Wood/Steel Trellis & Patio Cover Sub-Assembly Synthesis

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Structural Sub-Assembly**: Exterior residential or commercial open-lattice trellis (pergola) or solid-roofed patio cover spanning $L_{\text{rafter}}$ from an existing building ledger (or rear beam) to a front header beam supported on columns spaced at $S_{\text{post}}$, with post height $H_{\text{post}}$ above concrete piers/footings:
  - **Framing Material Options**: Sawn lumber / Glulam (DF-L #1/#2 or Alaskan Yellow Cedar / Redwood per AWC NDS 2024) OR structural steel HSS rafters, beams, and posts (ASTM A500 Gr. C per AISC 360-22).
  - **Lateral Stability Mechanism**:
    - **Attached to Main Building**: Roof diaphragm or diagonal bracing transfers horizontal wind/seismic forces back into the main building via ledger shear connections and out-of-plane tension ties ([Simpson DTT1Z](https://www.strongtie.com/decks_decksandfences/dtt_tie/p/dtt1) / [DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2)), while outer posts are pinned (`ABU44Z`/`ABU66Z`) or knee-braced.
    - **Freestanding Unbraced**: Columns act as cantilevers fixed at the base via Simpson Moment Post Bases ([MPB44Z / MPB66Z / MPB88Z](https://www.strongtie.com/standoffpostbases_castinplacepostbases/mpb_base/p/mpbz)), embedded steel posts, or moment-resisting steel base plates, OR braced via $45^\circ$ knee braces at the post-to-beam corners.

### 1.2 Governing Codes & Standards
- **Building Code**: [2024 IBC Section 1607.13.2.1 / 2025 CBC & IRC Appendix AH (Patio Covers)](https://codes.iccsafe.org/content/WABellevueBC2021P1/chapter-16-structural-design)
- **Wind & Seismic Loads**: [ASCE/SEI 7-22 Section 29.4 & Figure 29.4-2 (Open Signs and Single-Plane Open Frames), Section 30.11 (Attached Canopies), and Table 13.5-1 (Appendages)](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)
- **Material & Connector Standards**: AWC NDS 2024, ANSI/AISC 360-22, ACI 318-19 Chapter 17, and [Simpson Strong-Tie C-C-2026 Catalog](https://www.strongtie.com/)
- **Required Repository Database Tables**:
  - `database/asce_7/v7_22/ASCE7-22_Figure_29.4-2.csv` & `ASCE7-22_Figure_30.11-1A_1B.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Post_Bases_and_Caps_ABU_ABA_CBSQ_MPBZ_CC_BC.csv`

### 1.3 Complete Load Path & Force Transfer Mechanism
1. **Lattice Slats & Rafters**: Gravity loads ($D + L_r$) and vertical wind uplift/downforce transfer from $2\times 2$ / $2\times 4$ lattice slats into rafters spaced at $s_r$ ($16\text{ in.}$ or $24\text{ in.}$ o.c.).
2. **Rafter-to-Ledger & Rafter-to-Beam Connections**:
   - At the building wall: Rafters sit in Simpson face-mount hangers (`LUS26Z`/`LUS28Z`) on the wood ledger; vertical gravity and uplift reactions transfer through the hanger.
   - At the front header beam: Rafters sit on or frame into the header beam with Simpson hurricane ties (`H2.5AZ` or `H10A`) resisting net wind uplift.
3. **Ledger-to-Building Wall Attachment**:
   - Vertical shear transfers via staggered $1/2\text{ in.}$ lag screws or Simpson `1/4 in. SDS` / `SDWS` ledger screws into wall studs/rim joist (or expansion/epoxy anchors into concrete/CMU).
   - **Out-of-Plane Lateral Tension Pullout**: Per IRC Section R507.9.2 / IBC Section 1604.8.3, out-of-plane wind/seismic pullout forces transfer directly from rafters to building framing via at least two [Simpson DTT1Z / DTT2Z Deck Tension Ties](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2) (eliminating cross-grain tension in the wood ledger).
4. **Header Beam-to-Post & Post-to-Footing**:
   - Header beam transfers tributary gravity, uplift, and horizontal lateral shears through post caps ([Simpson LCE4Z / CCQ / BC](https://www.strongtie.com/miscconnectors_coldformedsteelconstruction/lce_cap/p/lce)) into the columns, down through post bases (`ABU` or moment-resisting `MPBZ`) into concrete piers/footings checked for soil bearing, overturning, and dead-weight uplift resistance.

---

## Section 2: Load Combinations & Internal Forces at the Critical Section

### 2.1 Gravity Loads (IBC Section 1607.13.2.1 & Table 1607.1)
- **Dead Load ($D$)**: Self-weight of slats, rafters, beams, and roofing (typically $5 - 10\text{ psf}$ for open wood/steel lattice trellis; $10 - 15\text{ psf}$ for solid patio cover).
- **Roof Live Load ($L_r$)**:
  - Standard uninhabitable roof/awning: $L_r = 20\text{ psf}$ (reducible per IBC Eq. 16-25 based on tributary area $A_t$ and slope $F$).
  - **Open Lattice Trellis Exception (IBC Sec. 1607.13.2.1)**: Where open lattice has $< 50\%$ solid area or meets local patio cover amendments, $L_r = 10\text{ psf}$ (verify local California municipal amendments).

### 2.2 Wind Drag on Open-Frame Trellis (ASCE 7-22 Figure 29.4-2) vs. Solid Canopy (Figure 30.11-1B)
1. **Horizontal Wind Drag on Open Trellis Framing (ASCE 7-22 Eq. 29.4-1)**:
   Query `ASCE7-22_Figure_29.4-2.csv` using solid-to-gross area ratio $\epsilon = A_{\text{solid}} / A_{\text{gross}}$ (for flat-sided members, $C_f = 1.6\text{ to }2.0$):
   $$F_{W,\text{horiz}} = q_z K_d G C_f A_f \quad (\text{lbs})$$
   where $K_d = 0.85$, $G = 0.85$, and $A_f$ is the projected vertical area of exposed beams, rafters, fascia, and top half of posts normal to the wind.
2. **Vertical Net Wind Uplift / Downforce ($p_{W,\text{vert}}$)**:
   - For solid or polycarbonate-sheeted patio covers: use `ASCE7-22_Figure_30.11-1A_1B.csv` ($p = q_h K_d GC_{p,\text{net}}$).
   - For open horizontal slats: apply net uplift/downforce pressure over the net solid horizontal plan area of the slats and rafters ($A_{\text{solid,plan}}$).

### 2.3 Seismic Force on Trellis / Patio Cover Canopy
- Evaluate horizontal seismic force $F_p = \max(0.4 S_{DS} I_p W_{\text{trib}} (H_f/R_\mu)(C_{AR}/R_{po}),\; 0.3 S_{DS} I_p W_{\text{trib}})$ from `ASCE7-22_Table_13.5-1.csv` (or $V = C_s W$ with $R = 1.5$ for freestanding cantilevered column systems per ASCE 7 Table 15.4-1).

---

## Section 3: Primary Member Verification (Rafters, Header Beam & Posts)

### 3.1 Rafter & Header Beam Flexure, Shear & Deflection (NDS 2024 / AISC 360)
For rafter span $L_r$ at spacing $s_r$ and header beam span $S_{\text{post}}$ supporting tributary width $L_r / 2$:
1. **Downward Gravity Governing Combination** ($D + L_r$ ASD with $C_D = 1.25$; $1.2D + 1.6L_r$ LRFD):
   $$M_{\text{down}} = \frac{w_{\text{down}} L^2}{8}, \qquad V_{\text{down}} = \frac{w_{\text{down}} L}{2}, \qquad \Delta_L = \frac{5 w_L L^4}{384 E I} \le \frac{L}{240}\text{ (or } L/180\text{)}$$
2. **Net Wind Uplift Reversal Check** ($0.6D + 0.6W_{\text{up}}$ ASD with $C_D = 1.60$; $0.9D + 1.0W_{\text{up}}$ LRFD):
   $$w_{\text{net,up}} = 0.6 w_{W,\text{up}} - 0.6 w_D \quad (\text{ASD})$$
   If $w_{\text{net,up}} > 0$, verify unbraced bottom edge flexural stability ($C_L$) of the rafter/header beam and net uplift reaction at all supports:
   $$R_{\text{up,rafter}} = \frac{w_{\text{net,up}} L_r}{2}, \qquad R_{\text{up,post}} = w_{\text{net,up}} \left(\frac{L_r}{2}\right) S_{\text{post}} - 0.6 W_{\text{beam/post}}$$

### 3.2 Column / Post Axial & Bending Interaction
- **Pinned Post (Braced by Building or Knee Braces, $K = 1.0$)**: Check axial compression stability factor $C_P$ (NDS Sec. 3.7.1) and combined wind load on post height $H_{\text{post}}$.
- **Freestanding Cantilevered Post ($K = 2.1$ per NDS Appendix G)**:
  $$M_{\text{post,base}} = V_{\text{top}} \cdot H_{\text{post}}, \qquad \left(\frac{f_c}{F'_c}\right)^2 + \frac{f_{bx}}{F'_{bx}(1 - f_c/F_{cEx})} \le 1.0 \quad (\text{NDS Eq. 3.9-3})$$

---

## Section 4: Sequential Connection Limit States Along the Load Path

### Step 4.1: Rafter-to-Beam & Rafter-to-Ledger Connectors (Simpson C-C-2026)
1. **Rafter-to-Header Beam Hurricane Tie (`H2.5AZ` / `H10A`)**:
   Query `Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`:
   $$R_{\text{up,rafter,ASD}} \le T_{\text{allow,H2.5AZ}} = 565\text{ lbs (DF/SP, } C_D=1.60\text{)}$$
2. **Rafter-to-Ledger Joist Hanger (`LUS26Z` / `LUS28Z`)**:
   Query `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv` and verify both downward gravity ($R_{\text{down}} \le D_{\text{allow,100}}$) and net wind uplift ($R_{\text{up}} \le U_{\text{allow,160}}$).

### Step 4.2: Ledger-to-Wall Vertical Shear & Out-of-Plane Tension Tie (`DTT1Z` / `DTT2Z`)
1. **Vertical Shear Fasteners (Lag Screws or Simpson `SDS` / `SDWS` Ledger Screws)**:
   Required fastener spacing $s_{\text{fastener}}$ along the ledger for vertical gravity load $v_{\text{grav}}$ (plf) and in-plane diaphragm shear $v_{\text{lat}}$ (plf):
   $$R_{\text{fastener}} = s_{\text{fastener}} \sqrt{v_{\text{grav}}^2 + v_{\text{lat}}^2} \le Z'_{\text{parallel/perp}} \quad (\text{NDS Ch. 12})$$
2. **Out-of-Plane Tension Pullout Tie ([Simpson DTT1Z / DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2))**:
   Total out-of-plane wind/seismic force $F_{\text{oop}}$ resisted by $N_{\text{ties}} \ge 2$ tension ties attached directly to the rafters and anchored into wall studs/plates or concrete/CMU wall:
   $$T_{\text{tie,ASD}} = \frac{F_{\text{oop,ASD}}}{N_{\text{ties}}} \le T_{\text{allow,DTT1Z (910 lbs) or DTT2Z (1,825 lbs / 1,500 lbs IRC)}}$$

### Step 4.3: Post-to-Beam Cap (`LCE4Z` / `BC` / `CCQ`) & Post-to-Footing Base (`ABU` / `MPBZ`)
Query `Simpson_C-C-2026_Post_Bases_and_Caps_ABU_ABA_CBSQ_MPBZ_CC_BC.csv`:
1. **Post Cap Verification**:
   $$R_{\text{up,post}} \le U_{\text{allow,cap}} \quad (\text{e.g., } 1,860\text{ lbs for paired LCE4 with SD10112 screws}), \qquad V_{\text{post}} \le F_{1,\text{allow,cap}}$$
2. **Post Base Verification**:
   - For pinned base ([Simpson ABU44Z / ABU66Z](https://www.strongtie.com/retrofitpostbases_postbases/abu_base/p/abu)):
     $$R_{\text{up,post}} \le U_{\text{allow,ABU}}, \qquad R_{\text{down,post}} \le D_{\text{allow,ABU}}$$
   - For moment-resisting post base ([Simpson MPB44Z / MPB66Z / MPB88Z](https://www.strongtie.com/standoffpostbases_castinplacepostbases/mpb_base/p/mpbz)):
     Verify the mandatory **Simpson MPBZ Simultaneous Combined Loading Interaction Equation**:
     $$\frac{P_{\text{design}}}{P_{\text{allow}}} + \frac{M_{\text{design}}}{M_{\text{allow}}} + \frac{V_{\text{design}}}{V_{\text{allow}}} \le 1.0$$
     where $P$ is either net uplift ($U$) or download ($D$), and for `MPB44Z`: $U_{\text{allow}} = 2,615\text{ lbs}$, $M_{\text{allow}} = 985\text{ lb-ft}$, $V_{\text{allow}} = 1,280\text{ lbs}$; for `MPB66Z`: $U_{\text{allow}} = 2,950\text{ lbs}$, $M_{\text{allow}} = 1,885\text{ lb-ft}$, $V_{\text{allow}} = 1,850\text{ lbs}$.

---

## Section 5: Supporting Foundation / Concrete Footing Verification (IBC Section 1806.2)

For each isolated square footing ($B_f \times B_f \times D_f$) or cylindrical drilled pier (diameter $d_{\text{pier}}$, embedment depth $h_{\text{pier}}$) with concrete unit weight $\gamma_c = 150\text{ pcf}$:
1. **Net Wind Uplift Overweight Check ($0.6D + 0.6W_{\text{up}}$ ASD)**:
   $$W_{\text{footing}} = \gamma_c B_f^2 D_f \implies 0.6(W_{\text{footing}} + P_{D,\text{post}}) \ge 0.6 P_{W,\text{up}} \implies W_{\text{footing}} \ge P_{W,\text{up}} - P_{D,\text{post}}$$
2. **Soil Bearing Pressure Check ($D + L_r$ or $D + 0.6W$)**:
   $$q_{\text{soil}} = \frac{P_{\text{down}} + W_{\text{footing}}}{B_f^2} \le q_{\text{allow,soil}} \quad (\text{typically } 1,500\text{ psf per IBC Table 1806.2})$$
3. **Drilled Pier Lateral Soil Bearing (IBC Section 1807.3.2.1 Nonconstrained Eq. 18-1)**:
   For freestanding cantilevered posts embedded or mounted on piers of diameter $b$ and depth $d$ with lateral soil bearing pressure $S_1 = 100 \cdot d/3\text{ psf/ft}$:
   $$d_{\text{req}} = \frac{A}{2}\left(1 + \sqrt{1 + \frac{4.36 h_e}{A}}\right), \qquad A = \frac{2.34 P_{\text{lat}}}{S_1 b}$$

---

## Section 6: Mandatory Detailing & Construction Notes
- **Pinned vs. Moment Post Base Restriction**: Standard post bases (`ABU`, `ABA`, `CBSQ`) have **zero rotational resistance** and shall NOT be used on freestanding, unbraced trellises or carports without top diaphragm attachment or knee braces. Use `MPBZ` moment post bases or embedded steel posts for unbraced freestanding columns.
- **1-Inch Standoff Requirement**: All exterior wood posts on concrete slabs/footings exposed to weather or water splash shall maintain a minimum $1\text{ in.}$ standoff above concrete per IBC Section 2304.12.1.3 (built into `ABU` and `MPBZ`).
- **Paired Post Caps**: Simpson `LCE4` / `LCE4Z` caps must be installed in pairs (one on each side of the post-to-beam joint) to achieve full tabulated uplift ($1,860\text{ lbs}$) and lateral ($1,355\text{ lbs}$) capacities.

---

## Section 7: Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :--- | :--- | :--- | :--- |
| **1** | Open-Frame Horizontal Wind Drag ($F_W$) | ASCE 7-22, Sec. 29.4 & Fig. 29.4-2 | $F_W = q_z K_d G C_f A_f$ ($C_f = 1.6\text{ to }2.0$ based on $\epsilon$) |
| **2** | Patio Cover Live Load & Net Uplift | 2024 IBC Sec. 1607.13.2.1 & ASCE 7 Fig. 30.11-1B | $w_{\text{net,up}} = 0.6 w_{W,\text{up}} - 0.6 w_D$ (ASD) |
| **3** | Rafter, Header Beam & Post Checks | AWC NDS 2024 Ch. 3 / AISC 360 Ch. F–H | Flexure, shear, $\Delta_L \le L/240$, and $P-M$ interaction $\le 1.0$ |
| **4.1** | Rafter Hanger & Hurricane Tie | Simpson C-C-2026 (`LUS` & `H2.5AZ`) | $R_{\text{down}} \le D_{\text{allow,100}};\; R_{\text{up}} \le U_{\text{allow,160}}$ |
| **4.2** | Ledger Shear & Out-of-Plane Tension Tie | NDS Ch. 12, IBC Sec. 1604.8.3 & `DTT2Z` | $R_{\text{screw}} \le Z'$; $T_{\text{oop}} \le N_{\text{ties}} \cdot T_{\text{allow,DTT2Z}}$ |
| **4.3** | Post Cap (`LCE4Z`/`CCQ`) & Base (`ABU`/`MPBZ`) | Simpson C-C-2026, ESR-3096 & ESR-3050 | MPBZ: $(P/P_{\text{allow}}) + (M/M_{\text{allow}}) + (V/V_{\text{allow}}) \le 1.0$ |
| **5** | Footing Uplift, Bearing & Pier Lateral Depth | 2024 IBC, Table 1806.2 & Sec. 1807.3.2.1 | $0.6 W_{\text{ftg}} \ge 0.6 P_{\text{net,up}}$; $q_{\text{soil}} \le q_{\text{allow}}$; $d \ge d_{\text{req}}$ (Eq. 18-1) |
