# Wood-Frame Shear Wall & Holdown Anchorage Design Procedure (SDPWS 2021 / IBC 2024)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Section 2305 & 2306 ([IBC/SDPWS Provisions](https://bayarearetrofit.com/wp-content/uploads/2015-Wind-and-Seismic.pdf)).
  - **ANSI/AWC SDPWS-2021**: *Special Design Provisions for Wind and Seismic*, Section 4.3 (Wood-Frame Shear Walls) ([ANSI/AWC SDPWS Standard](https://bayarearetrofit.com/wp-content/uploads/2015-Wind-and-Seismic.pdf), [STRUCTURE Magazine SDPWS 2021 Overview](https://www.structuremag.org/article/2021-special-design-provisions-for-wind-and-seismic/)).
  - **ANSI/AWC NDS-2024**: *National Design Specification for Wood Construction* (Boundary Posts, Sill Plate Bearing & Anchor Bolts).
  - **ACI 318-19**: Chapter 17 (Concrete Anchorage of Holdown Bolts and Sill Bolts).
  - **Simpson Strong-Tie Wood Construction Connectors Catalog (C-C-2026)**: Pre-deflected Holdowns ([HDU Series](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdu_holdown/p/hdu), [HDUE Series](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdue_holdown/p/hdue)), Deck/Light Holdowns ([DTT1Z](https://www.strongtie.com/decks_decksandfences/dtt_tie/p/dtt1), [DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2)), and Lateral Tie Plates ([LTP4/LTP5](https://www.strongtie.com/framinganglesandplates_anglesandplates/ltp_plate/p/ltp), [A35](https://www.strongtie.com/framinganglesandplates_anglesandplates/a35_angle/p/a35)).
- **Referenced Repository Databases**:
  - `database/nds_wood/v2024/sdpws/SDPWS-2021_Table_4.3A_Shear_Walls.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`
- **Design Philosophies (Dual ASD & LRFD)**:
  - **Allowable Stress Design (ASD)**: $\Omega = 2.00 \implies v_{ASD} = \frac{v_{nominal}}{2.00}$ (SDPWS Section 4.3.3).
  - **Load and Resistance Factor Design (LRFD)**: $\phi_D = 0.80 \implies \phi v_n = 0.80 \cdot v_{nominal}$ (SDPWS Section 4.3.3).
  - **Seismic vs. Wind Nominal Capacities**: For wood structural panels (WSP), $v_w = 1.40 \cdot v_s$.

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $h$ | Shear wall clear height (top of sill plate to top of top plate) | $\text{ft}$ | Architectural / Framing Elevations |
| $b_s$ | Length of full-height shear wall segment | $\text{ft}$ | Structural Framing Plan |
| $V_{ASD}, V_{LRFD}$ | In-plane horizontal shear force applied to top of shear wall segment | $\text{lbs}$ | Diaphragm Flexible/Rigid Distribution |
| $w_{DL}$ | Uniform Tributary Dead Load acting along top of shear wall | $\text{plf}$ | Gravity Load Takedown ($0.6D$ ASD / $0.9D$ LRFD) |
| $\text{Category}_{WSP}$ | Sheathing category (`Structural I`, `Sheathing`, `Plywood Siding`, `Particleboard`) | — | SDPWS Table 4.3A |
| $t_{panel}, d_{nail}, s_{edge}$ | Panel thickness ($3/8"$, $7/16"$, $15/32"$), nail size (`6d`, `8d`, `10d`), edge spacing ($6", 4", 3", 2"$) | $\text{in.}$ | SDPWS Table 4.3A |
| $G$ | Specific gravity of wall framing studs/plates (DF-L $G = 0.50$, SPF $G = 0.42$) | — | NDS-2024 Table 12.3.3A |
| $E, A_{chord}$ | Elastic modulus ($\text{psi}$) and gross area ($\text{in.}^2$) of end boundary chord post | $\text{psi}, \text{in.}^2$ | NDS-2024 Supplement (`2-2x4`, `4x4`, `4x6`, `6x6`) |
| $\Delta_{holdown}$ | Holdown vertical elongation at tabulated allowable load $T_{allow}$ | $\text{in.}$ | `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv` |

---

## 3. Adjustment Factors & Governing Mechanics

### 3.1 Analytical Method Selection (SDPWS Section 4.3.5)
1. **Individual Full-Height Wall Segments (Segmented Shear Wall Method - SDPWS 4.3.5.1)**:
   - Each full-height wall segment of width $b_s$ is provided with overturning holdowns at both ends where net uplift occurs. Openings are ignored except for defining segment widths $b_s$.
2. **Perforated Shear Wall Method (SDPWS 4.3.5.3 & Table 4.3.3.5)**:
   - Holdowns are required only at the two extreme ends of the perforated shear wall line. Intermediate piers between openings lack holdowns, and total shear capacity is reduced by the Perforated Shear Wall Adjustment Factor $C_o$ from `SDPWS-2021_Table_4.3A_Shear_Walls.csv` (Supplemental Table 4.3.3.5) based on maximum opening height ratio $h_o / h$ and percent full-height sheathing $\sum L_i / L_{tot}$.
3. **Force Transfer Around Openings (FTAO - SDPWS 4.3.5.2)**:
   - Rational analysis (Diekmann method) using continuous horizontal strap ties ([CS16](https://www.strongtie.com/coiledstraps_specialtystraps/cs_strap/p/cs), [MSTA](https://www.strongtie.com/straightstraps_strapsandties/msta_strap/p/msta), [MSTC](https://www.strongtie.com/straightstraps_strapsandties/mstc_strap/p/mstc)) and full-height blocking above and below window/door openings to transfer corner forces around the opening.

### 3.2 Shear Wall Aspect Ratio Limits & Adjustment Factor ($C_{ar}$, SDPWS Table 4.3.4 & Sec. 4.3.4.2)
- **Maximum Permitted Aspect Ratio ($h / b_s$)**:
  - Blocked Wood Structural Panels (WSP): $h / b_s \le 3.5:1$ (For Wind and Seismic).
  - Unblocked Wood Structural Panels (WSP): $h / b_s \le 2.0:1$.
  - Particleboard Sheathing: $h / b_s \le 2.0:1$.
- **Seismic Aspect Ratio Capacity Adjustment Factor ($C_{ar}$) for $2.0 < h / b_s \le 3.5$**:
  - Where $h / b_s \le 2.0$: $C_{ar} = 1.00$ (no reduction).
  - Where $2.0 < h / b_s \le 3.5$ under **Seismic** loading (no reduction required for Wind where $h/b_s \le 3.5$):
    - **SDPWS-2021 Equation 4.3-2**:
      $$C_{ar} = 1.25 - 0.125 \cdot \left(\frac{h}{b_s}\right)$$
    - **SDPWS-2015 / Conservative Plan-Check Factor** (where required by local amendments or multi-panel pier rules):
      $$C_{ar,alt} = \frac{2 \cdot b_s}{h}$$

### 3.3 Specific Gravity ($C_{sp}$), Unblocked ($C_{ub}$), and Two-Sided Sheathing Rules
- **Specific Gravity Factor ($C_{sp}$)**: For framing with $G < 0.50$, $C_{sp} = 1.0 - (0.50 - G) \le 1.00$ ($0.92$ for SPF, $0.93$ for HF, $1.00$ for DF-L/SP).
- **Unblocked WSP Adjustment Factor ($C_{ub}$)**: If horizontal panel edges are not blocked and edge nailing is $6"$ o.c., multiply nominal capacity by $C_{ub}$ from SDPWS Table 4.3.3.2 (e.g., $C_{ub} = 0.8$ for $16"$ o.c. studs with vertical panels and $12"$ field nailing).
- **Sheathing on Both Sides of Wall (SDPWS Section 4.3.3.3)**:
  - **Same Material & Fastener Schedule on Both Sides**: Combined nominal shear capacity $= 2.0 \times v_{single\text{-}side}$ and $G_{a,combined} = 2.0 \times G_{a,single\text{-}side}$.
  - **Dissimilar Materials or Asymmetric WSP on Opposite Sides**: For Wind, capacities may be summed if $G_a$ values are compatible; for Seismic, take the greater of: (a) $2.0 \times$ the smaller single-side capacity, or (b) $1.0 \times$ the stronger single-side capacity. (Combining gypsum wallboard with WSP for seismic resistance is **prohibited**).

---

## 4. Step-by-Step Calculation Procedure (Dual ASD & LRFD)

### Step 1: Wall Segment Geometry & Aspect Ratio Check
1. Identify each full-height shear wall segment length $b_s$ and clear height $h$.
2. Compute $h / b_s$ and verify $h / b_s \le 3.5$. Compute $C_{ar}$:
   $$C_{ar} = \begin{cases} 1.00 & \text{if } h/b_s \le 2.0 \text{ (or Wind loading)} \\ 1.25 - 0.125(h/b_s) & \text{if } 2.0 < h/b_s \le 3.5 \text{ (Seismic, SDPWS-2021 Eq. 4.3-2)} \end{cases}$$

### Step 2: Shear Wall In-Plane Unit Shear Demand & Capacity
1. Compute induced unit shear in the wall segment:
   $$v_{ASD} = \frac{V_{ASD}}{b_s} \quad (\text{plf}), \qquad v_{LRFD} = \frac{V_{LRFD}}{b_s} \quad (\text{plf})$$
2. Look up nominal unit shear capacity $v_s$ or $v_w$ and apparent stiffness $G_a$ from `SDPWS-2021_Table_4.3A_Shear_Walls.csv`.
3. Compute adjusted design unit shear capacity:
   - **ASD Allowable Unit Shear**:
     $$v_{allow} = \frac{v_{nominal} \cdot C_{sp} \cdot C_{ar} \cdot C_{ub} \cdot C_o}{2.00} \quad (\text{plf})$$
   - **LRFD Factored Unit Resistance**:
     $$\phi v_n = 0.80 \cdot v_{nominal} \cdot C_{sp} \cdot C_{ar} \cdot C_{ub} \cdot C_o \quad (\text{plf})$$
4. Verify $D/C_{shear} = v_{ASD} / v_{allow} \le 1.00$ (or $v_{LRFD} / (\phi v_n) \le 1.00$).

### Step 3: Overturning Chord Forces & Boundary Post Design
1. Take moments about the compression toe of the shear wall segment (SDPWS Section 4.3.6.1):
   - Gross Overturning Moment:
     $$M_{OT} = V \cdot h \quad (\text{lb-ft})$$
   - Resisting Gravity Dead Load Moment (using $0.6D$ for ASD or $0.9D$ for LRFD per ASCE 7-22 Section 2.4 / 2.3):
     $$M_{R,ASD} = 0.6 \cdot w_{DL} \cdot \frac{b_s^2}{2}, \qquad M_{R,LRFD} = 0.9 \cdot w_{DL} \cdot \frac{b_s^2}{2} \quad (\text{lb-ft})$$
2. **Net Holdown Tension Force ($T$)**:
   $$T_{ASD} = \max\left(0,\; \frac{M_{OT,ASD} - M_{R,ASD}}{b_s}\right) = v_{ASD} \cdot h - 0.3 \cdot w_{DL} \cdot b_s \quad (\text{lbs})$$
   $$T_{LRFD} = \max\left(0,\; \frac{M_{OT,LRFD} - M_{R,LRFD}}{b_s}\right) = v_{LRFD} \cdot h - 0.45 \cdot w_{DL} \cdot b_s \quad (\text{lbs})$$
   *(Note: If conservative chord-centerline lever arm $d_{eff} = b_s - b_{post}$ is required by local jurisdiction, divide net moment by $d_{eff}$).*
3. **Maximum Boundary Post Compression Force ($C$)**:
   $$C_{ASD} = v_{ASD} \cdot h + 1.0 \cdot w_{DL} \cdot \frac{b_s}{2} + P_{point,D+0.75L} \quad (\text{lbs})$$
   Check both axial compression stability of the end post ($f_c = C / A_{post} \le F'_c$, with weak-axis braced by sheathing $l_{e,x}/d_x = 0$) AND **sill plate compression perpendicular to grain** ($f_{c\perp} = C / A_{post} \le F'_{c\perp} = F_{c\perp} \cdot C_b$).

### Step 4: Simpson Holdown Selection & Vertical Elongation ($\Delta_a$)
1. From `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`, select a holdown model ([HDU2–HDU14](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdu_holdown/p/hdu), [HDUE3–HDUE17](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdue_holdown/p/hdue), or [DTT1Z/DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2)) matching the wood post thickness $t_{post}$ and species (`DF/SP` or `SPF/HF`) such that:
   $$T_{ASD} \le T_{allow,Holdown} \quad (C_D = 1.60)$$
2. Compute total vertical holdown/anchorage elongation $\Delta_a$ at the demand level being evaluated:
   $$\Delta_a = \Delta_{holdown,tab} \cdot \left(\frac{T_{demand}}{T_{allow,Holdown}}\right) + \frac{T_{demand} \cdot L_{unbonded}}{E_s \cdot A_{rod}} + \Delta_{shrinkage} \quad (\text{in.})$$
   Where $\Delta_{holdown,tab}$ is the catalog deflection at allowable load $T_{allow,Holdown}$.

### Step 5: Shear Wall In-Plane Deflection Check (SDPWS Eq. 4.3-1)
1. Compute the 3-term horizontal story drift at the top of the shear wall segment (SDPWS Section 4.3.2, Equation 4.3-1) ([WoodWorks Shear Wall & Diaphragm Guide](https://www.woodworks.org/wp-content/uploads/presentation_slides-STRASSER-Shearwalls-and-Diaphragms-WDS-200225.pdf)):
   $$\delta_{sw} = \underbrace{\frac{8 \cdot v \cdot h^3}{E \cdot A \cdot b_s}}_{\text{Cantilever Bending}} + \underbrace{\frac{v \cdot h}{1000 \cdot G_a}}_{\text{Panel Shear + Nail Slip}} + \underbrace{\frac{h \cdot \Delta_a}{b_s}}_{\text{Holdown Rigid-Body Rotation}} \quad (\text{in.})$$
   Where:
   - $v$ = Induced unit shear ($\text{plf}$) at the load level (ASD or amplified seismic story drift level).
   - $h$ = Shear wall height ($\text{ft}$).
   - $b_s$ = Shear wall segment length ($\text{ft}$).
   - $E$ = Elastic modulus of boundary chord post ($\text{psi}$).
   - $A$ = Gross cross-sectional area of boundary chord post ($\text{in.}^2$).
   - $G_a$ = Apparent shear wall shear stiffness from SDPWS Table 4.3A ($\text{kips/in.}$).
   - $\Delta_a$ = Total vertical elongation of the holdown anchorage system ($\text{in.}$) at the evaluated load level.
2. **Seismic Story Drift Check (ASCE 7-22 Section 12.8.6 & 12.12.1)**:
   - Evaluate $\delta_{xe}$ under strength-level seismic forces ($1.0E$), then multiply by the deflection amplification factor $C_d / I_e$ ($C_d = 4.0$ for light-frame WSP shear walls with $R = 6.5$):
     $$\Delta_{story} = \frac{C_d \cdot \delta_{sw,LRFD}}{I_e} \le \Delta_{allow} = 0.020 \cdot h_{sx} \text{ (or } 0.025 \cdot h_{sx}\text{)}$$

### Step 6: Sill Plate Shear Transfer & Anchor Bolts
1. **Top-of-Wall Shear Transfer**: Check boundary nailing or [Simpson LTP4/A35](https://www.strongtie.com/framinganglesandplates_anglesandplates/ltp_plate/p/ltp) clips from rim joist/blocking into double top plates, and face-nailing between double top plates.
2. **Sill Plate Anchor Bolts (NDS Section 12.3)**:
   - Compute parallel-to-grain single-shear capacity $Z'_\parallel = Z_\parallel \cdot C_D$ of $1/2"$, $5/8"$, or $3/4"$ diameter anchor bolts in $2\text{x}$ or $3\text{x}$ sill plate against concrete ($t_m \ge 6"$):
     $$N_{bolts} = \left\lceil \frac{V_{ASD}}{Z'_\parallel} \right\rceil, \qquad s_{bolt} \le 6\text{ ft o.c. (4 ft o.c. in SDC D/E/F if } h > 2\text{ stories)}$$
   - Minimum of **two (2) anchor bolts** per sill plate piece, located within $12"$ (and $\ge 4"$ or $7 d_b$) from each end of the plate (IBC Section 2308.3.1 / SDPWS 4.3.6.4).

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State / Component | Demand Symbol | Capacity Symbol | Governing Code / Catalog Reference | Acceptance Criterion |
| :--- | :--- | :--- | :--- | :--- |
| **Wall Segment Aspect Ratio** | $h / b_s$ | $3.5:1$ (Blocked WSP) | SDPWS Table 4.3.4 | $(h/b_s) / 3.5 \le 1.00$ |
| **In-Plane Unit Shear (ASD)** | $v_{ASD}$ ($\text{plf}$) | $v_{allow} = 0.50 v_{nom} C_{sp} C_{ar} C_{ub} C_o$ | SDPWS Sec. 4.3.3 & Table 4.3A | $v_{ASD} / v_{allow} \le 1.00$ |
| **In-Plane Unit Shear (LRFD)** | $v_{LRFD}$ ($\text{plf}$) | $\phi v_n = 0.80 v_{nom} C_{sp} C_{ar} C_{ub} C_o$ | SDPWS Sec. 4.3.3 & Table 4.3A | $v_{LRFD} / (\phi v_n) \le 1.00$ |
| **Holdown Uplift Capacity** | $T_{ASD}$ ($\text{lbs}$) | $T_{allow,Holdown}$ ($\text{lbs}$) | Simpson C-C-2026 (`HDU`/`HDUE`/`DTT`) | $T_{ASD} / T_{allow,Holdown} \le 1.00$ |
| **End Post Net Tension** | $T_{ASD}$ ($\text{lbs}$) | $F'_t \cdot A_{net}$ ($\text{lbs}$) | NDS-2024 Sec. 3.8 | $T_{ASD} / (F'_t A_{net}) \le 1.00$ |
| **End Post Axial Compression** | $C_{ASD}$ ($\text{lbs}$) | $F'_c \cdot A_{gross}$ ($\text{lbs}$) | NDS-2024 Sec. 3.7 | $C_{ASD} / (F'_c A_{gross}) \le 1.00$ |
| **Sill Plate Bearing ($c\perp$)** | $f_{c\perp} = C_{ASD} / A_{post}$ | $F'_{c\perp} = F_{c\perp} \cdot C_b$ | NDS-2024 Sec. 3.10 | $f_{c\perp} / F'_{c\perp} \le 1.00$ |
| **Sill Anchor Bolt Shear** | $V_{ASD}$ ($\text{lbs}$) | $N_{bolts} \cdot Z'_\parallel$ ($\text{lbs}$) | NDS-2024 Table 12E & ACI 318 Ch. 17 | $V_{ASD} / (N_{bolts} Z'_\parallel) \le 1.00$ |
| **Story Drift ($\Delta_{story}$)** | $C_d \delta_{sw,LRFD} / I_e$ | $\Delta_{allow} = 0.020 h_{sx}$ | SDPWS Eq. 4.3-1 & ASCE 7-22 Table 12.12-1 | $\Delta_{story} / \Delta_{allow} \le 1.00$ |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Steel Plate Washers on Foundation Sill Bolts (SDPWS Section 4.3.6.4.3)**:
   - A minimum **$0.229" \times 3" \times 3"$ steel plate washer** is **mandatory** on every foundation sill anchor bolt in all shear walls assigned to **SDC D, E, or F**, and in SDC A–C whenever nominal unit shear exceeds $700\text{ plf}$ ($v_s > 700\text{ plf}$ or $v_w > 980\text{ plf}$). Standard round cut washers will be flagged during plan check.
   - The hole in the plate washer shall be within $1/16"$ of the bolt diameter, and the edge of the plate washer must extend to within $1/2"$ of the sheathed edge of the sill plate.
2. **3x Framing at Adjoining Panel Edges & Sill Plate (SDPWS Table 4.3A Footnote 3)**:
   - Whenever panel edge fastener spacing is **$2\text{ in. o.c.}$**, or where nominal unit shear exceeds $700\text{ plf}$ ($v_{ASD} > 350\text{ plf}$ Seismic), **minimum $3\text{x}$ ($2.5"$ actual thickness) framing** is required at adjoining panel edges and for the foundation sill plate. If $2\text{x}$ studs are used at panel joints, detail a stitched double-stud (`2-2x`) with staggered `10d` nails at $6"$ o.c.
3. **Holdown Post Size Mismatch & Raised Holdown Installation ([Simpson HDU Page](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdu_holdown/p/hdu))**:
   - Verify that the wood post thickness called out on the framing plan matches the exact post size used to look up the `HDU` capacity in `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv` (e.g., `HDU8-SDS2.5` is rated for $6,760\text{ lbs}$ on a `2-2x4` [$3.0"$] post, vs. $7,870\text{ lbs}$ on a `4x4` [$3.5"$] or `3-2x4` [$4.5"$] post in DF/SP).
   - If the holdown is raised above the sill plate to clear anchor bolt couplers, include the unbonded anchor rod elongation $\Delta_{rod} = T L_{rod} / (E_s A_s)$ in $\Delta_a$.
4. **Unused Holdowns in Holdown Schedule**:
   - Remove any holdown marks from the Structural General Notes / Holdown Schedule that do not appear on the Framing or Foundation Plans (a frequent municipal plan check markup).

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Design a single-story blocked exterior wood structural panel shear wall segment in Seismic Design Category D ($R = 6.5, C_d = 4.0, I_e = 1.0$):
- **Wall Segment Geometry**: Clear height $h = 10.0\text{ ft}$, Segment width $b_s = 4.0\text{ ft}$.
- **Applied Loads**:
  - Factored LRFD Seismic Shear: $V_{LRFD} = 3,200\text{ lbs}$ ($1.0E$).
  - Allowable ASD Seismic Shear: $V_{ASD} = 0.7 \times 3,200 = 2,240\text{ lbs}$ ($0.7E$).
  - Tributary Gravity Dead Load: $w_{DL} = 250\text{ plf}$.
- **Materials**:
  - Framing: Douglas Fir-Larch No. 2 ($G = 0.50, C_{sp} = 1.00, E = 1,600,000\text{ psi}, F_{c\perp} = 625\text{ psi}$).
  - Boundary End Posts: `4x4` DF-L ($3.5" \times 3.5", A = 12.25\text{ in.}^2$).
  - Sheathing: Single-sided $15/32"$ `Structural I` OSB panels with `10d` common nails (`3" x 0.148"`).

### 7.2 Step-by-Step Solution

#### 1. Aspect Ratio & Adjustment Factor ($C_{ar}$)
$$\frac{h}{b_s} = \frac{10.0\text{ ft}}{4.0\text{ ft}} = 2.50 \le 3.50 \quad (\text{SDPWS Table 4.3.4 Blocked WSP}) \implies \textbf{OK}$$
Since $2.0 < h/b_s = 2.50 \le 3.5$, compute the SDPWS-2021 Eq. 4.3-2 aspect ratio factor:
$$C_{ar} = 1.25 - 0.125 \times (2.50) = 1.25 - 0.3125 = 0.9375$$
*(Note: Under conservative SDPWS-2015 / IBC $2 b_s / h$ rule, $C_{ar,alt} = 2(4.0)/10.0 = 0.800$. We verify both below).*

#### 2. Unit Shear Demand & Sheathing Nailing Selection (`SDPWS-2021_Table_4.3A_Shear_Walls.csv`)
- Induced Unit Shear:
  $$v_{ASD} = \frac{2,240\text{ lbs}}{4.0\text{ ft}} = 560.0\text{ plf}, \qquad v_{LRFD} = \frac{3,200\text{ lbs}}{4.0\text{ ft}} = 800.0\text{ plf}$$
- Try $15/32"$ `Structural I` OSB with `10d` common nails at **$3\text{ in. o.c.}$** edge spacing (`10d @ 3"/12"`):
  - From `SDPWS-2021_Table_4.3A_Shear_Walls.csv`: $v_s = 1,330\text{ plf}$, $G_a = 36.0\text{ kips/in.}$ (OSB).
  - **With SDPWS-2021 $C_{ar} = 0.9375$**:
    $$v_{allow} = \frac{1,330 \times 1.00 \times 0.9375}{2.00} = 623.4\text{ plf} \ge 560.0\text{ plf} \quad (D/C = 0.898 \le 1.00) \implies \textbf{OK}$$
    $$\phi v_n = 0.80 \times 1,330 \times 1.00 \times 0.9375 = 997.5\text{ plf} \ge 800.0\text{ plf} \quad (D/C = 0.802 \le 1.00) \implies \textbf{OK}$$
  - **Even with conservative $2 b_s / h = 0.800$**:
    $$v_{allow,alt} = \frac{1,330 \times 0.800}{2.00} = 532.0\text{ plf} \quad (\text{If } 2b_s/h \text{ governs, step up to } 2"\text{ o.c. w/ } 3\text{x framing: } v_{allow} = 1740 \times 0.8 / 2 = 696\text{ plf}).$$

#### 3. Overturning Chord Forces & Holdown Selection (`Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`)
- **ASD Overturning Tension**:
  $$M_{OT,ASD} = 2,240 \times 10.0 = 22,400\text{ lb-ft}$$
  $$M_{R,ASD} = 0.6 \times 250 \times \frac{4.0^2}{2} = 1,200\text{ lb-ft}$$
  $$T_{ASD} = \frac{22,400 - 1,200}{4.0} = 5,300\text{ lbs}$$
- **Select Simpson Holdown** on `4x4` ($3.5" \times 3.5"$) DF-L post:
  - Try **Simpson [HDU5-SDS2.5](https://www.strongtie.com/sdsscrewholdowns_holdowns/hdu_holdown/p/hdu)** (`14 ga`, $5/8"$ anchor bolt, `(14) 1/4" x 2.5" SDS` screws):
    - From `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`:
      $$T_{allow,HDU5} = 5,645\text{ lbs} \ge 5,300\text{ lbs} \quad (D/C = 0.939 \le 1.00) \implies \textbf{OK}$$
    - Tabulated deflection at allowable load: $\Delta_{holdown,tab} = 0.115\text{ in.}$
    - Scaled holdown elongation at $T_{ASD} = 5,300\text{ lbs}$:
      $$\Delta_{a,ASD} = 0.115 \times \left(\frac{5,300}{5,645}\right) = 0.108\text{ in.}$$
- **Compression Post & Sill Plate Bearing Check**:
  $$C_{ASD} = 560.0 \times 10.0 + 1.0 \times 250 \times \frac{4.0}{2} = 5,600 + 500 = 6,100\text{ lbs}$$
  $$f_{c\perp} = \frac{6,100\text{ lbs}}{12.25\text{ in.}^2} = 498.0\text{ psi} \le F'_{c\perp} = 625\text{ psi} \quad (D/C = 0.797 \le 1.00) \implies \textbf{OK}$$

#### 4. Shear Wall Deflection & Story Drift Check (SDPWS Eq. 4.3-1)
- Evaluate at Strength Level ($1.0E$, $v_{LRFD} = 800.0\text{ plf}$, $T_{LRFD} = 800(10) - 0.45(250)(4) = 7,550\text{ lbs}$, $\Delta_{a,LRFD} = 0.115 \times (7550 / 5645) = 0.154\text{ in.}$):
  $$\delta_{sw,LRFD} = \frac{8 \times 800.0 \times 10.0^3}{1,600,000 \times 12.25 \times 4.0} + \frac{800.0 \times 10.0}{1000 \times 36.0} + \frac{10.0 \times 0.154}{4.0}$$
  $$\delta_{sw,LRFD} = 0.0816 + 0.2222 + 0.3850 = 0.689\text{ in.}$$
- Amplified Seismic Story Drift ($C_d = 4.0, I_e = 1.0$):
  $$\Delta_{story} = \frac{4.0 \times 0.689}{1.0} = 2.756\text{ in.} \le \Delta_{allow} = 0.025 \times 120" = 3.00\text{ in.} \quad (D/C = 0.919 \le 1.00) \implies \textbf{OK}$$
- **Required Detailing Note**: Because $v_s = 1,330\text{ plf} > 700\text{ plf}$ and SDC = D, specify **`3x4` PT DF-L sill plate** with `(3) 5/8" dia. anchor bolts` and **$0.229" \times 3" \times 3"$ steel plate washers** per SDPWS Section 4.3.6.4.3.
