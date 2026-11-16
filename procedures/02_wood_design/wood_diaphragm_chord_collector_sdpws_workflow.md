# Wood Structural Panel Diaphragm, Chord, and Collector Design Procedure (SDPWS 2021 / IBC 2024)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 23 ([IBC Wood Provisions](https://bayarearetrofit.com/wp-content/uploads/2015-Wind-and-Seismic.pdf)).
  - **ANSI/AWC SDPWS-2021**: *Special Design Provisions for Wind and Seismic*, Section 4.2 (Wood-Frame Diaphragms) ([ANSI/AWC SDPWS Standard](https://bayarearetrofit.com/wp-content/uploads/2015-Wind-and-Seismic.pdf), [STRUCTURE Magazine SDPWS 2021 Overview](https://www.structuremag.org/article/2021-special-design-provisions-for-wind-and-seismic/)).
  - **ANSI/AWC NDS-2024**: *National Design Specification for Wood Construction* (Member & Connection Design).
  - **ASCE/SEI 7-22**: *Minimum Design Loads and Associated Criteria for Buildings and Other Structures*, Chapter 12 (Seismic Diaphragm Design Forces $F_{px}$, Collector $\Omega_0$ Amplification) & Chapters 26–30 (Wind Loads).
  - **Simpson Strong-Tie Wood Construction Connectors Catalog (C-C-2026)**: Coiled Straps ([CS Series](https://www.strongtie.com/coiledstraps_specialtystraps/cs_strap/p/cs), [CMST/CMSTC Series](https://www.strongtie.com/coiledstraps_specialtystraps/cmst_strap/p/cmst)), Precut Straight Straps ([LSTA](https://www.strongtie.com/straightstraps_strapsandties/lsta_strap/p/lsta), [MSTA](https://www.strongtie.com/straightstraps_strapsandties/msta_strap/p/msta), [MSTC](https://www.strongtie.com/straightstraps_strapsandties/mstc_strap/p/mstc), [MST](https://www.strongtie.com/straightstraps_strapsandties/mst_strap/p/mst)), and Lateral Plates ([LTP4/LTP5](https://www.strongtie.com/framinganglesandplates_anglesandplates/ltp_plate/p/ltp), [A35](https://www.strongtie.com/framinganglesandplates_anglesandplates/a35_angle/p/a35)).
- **Referenced Repository Databases**:
  - `database/nds_wood/v2024/sdpws/SDPWS-2021_Table_4.2A_Blocked_Diaphragms.csv`
  - `database/nds_wood/v2024/sdpws/SDPWS-2021_Table_4.2C_Unblocked_Diaphragms.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`
- **Design Philosophies (Dual ASD & LRFD)**:
  - **Allowable Stress Design (ASD)**: $\Omega = 2.00 \implies v_{ASD} = \frac{v_{nominal}}{2.00}$ (SDPWS Section 4.2.3).
  - **Load and Resistance Factor Design (LRFD)**: $\phi_D = 0.80 \implies \phi v_n = 0.80 \cdot v_{nominal}$ (SDPWS Section 4.2.3).
  - **Nominal Shear Relationship**: Tabulated nominal wind unit shear capacity is $v_w = 1.40 \cdot v_s$, where $v_s$ is the tabulated nominal seismic unit shear capacity.

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $L$ | Diaphragm span length perpendicular to lateral load direction | $\text{ft}$ | Architectural / Structural Framing Plan |
| $W$ | Diaphragm width (depth) parallel to lateral load direction | $\text{ft}$ | Architectural / Structural Framing Plan |
| $w_u, w_a$ | Factored (LRFD) or Allowable (ASD) uniform lateral load along diaphragm | $\text{plf}$ | ASCE 7-22 Wind ($0.6W$ / $1.0W$) or Seismic ($0.7E$ / $1.0E$, $F_{px}$) |
| $\text{Grade}_{WSP}$ | Wood Structural Panel sheathing grade (`Structural I` vs. `Sheathing / Single-Floor`) | — | SDPWS Table 4.2A / 4.2C |
| $t_{panel}$ | Nominal panel thickness ($5/16"$, $3/8"$, $7/16"$, $15/32"$, $19/32"$) and type (`OSB` vs. `PLY`) | $\text{in.}$ | SDPWS Table 4.2A / 4.2C |
| $d_{nail}, s_{edge}$ | Common nail size (`6d`, `8d`, `10d`) and boundary/edge spacing ($6"$, $4"$, $2.5"$, $2"$) | $\text{in.}$ | SDPWS Table 4.2A / 4.2C |
| $b_{framing}$ | Nominal width of framing at adjoining panel edges and boundaries ($2\text{x}$ vs. $3\text{x}$) | $\text{in.}$ | SDPWS Table 4.2A ($3\text{x}$ req'd for 10d at $\le 2.5"$) |
| $G$ | Specific gravity of diaphragm framing lumber (e.g., DF-L $G = 0.50$, SPF $G = 0.42$) | — | NDS-2024 Table 12.3.3A |
| $E, A$ | Modulus of elasticity ($\text{psi}$) and cross-sectional area ($\text{in.}^2$) of diaphragm chord | $\text{psi}, \text{in.}^2$ | NDS-2024 Supplement |
| $\Delta_c, x$ | Chord splice slip ($\text{in.}$) at distance $x$ ($\text{ft}$) from diaphragm midspan | $\text{in.}, \text{ft}$ | SDPWS Section 4.2.2 / Simpson Strap Data |

---

## 3. Adjustment Factors & Governing Mechanics

### 3.1 Flexible vs. Rigid Diaphragm Classification
- **ASCE 7-22 Section 12.3.1.1 / SDPWS Section 4.2.5**:
  - Untopped wood structural panel diaphragms are permitted to be idealized as **flexible** where supported by concrete/masonry walls or light-frame wood shear walls meeting ASCE 7 Section 12.3.1.1.
  - Strictly, a diaphragm is **flexible** when the maximum in-plane deflection of the diaphragm under lateral load is more than two times the average story drift of the associated vertical resisting elements:
    $$\delta_{dia} > 2 \cdot \Delta_{wall,avg}$$
  - Where concrete tilt-up or masonry walls support large wood roof diaphragms, the diaphragm behaves as a simple horizontal beam spanning between vertical shear walls (tributary width distribution). Where wood diaphragms have heavy concrete topping or stiff geometry over flexible frames, perform an envelope analysis (flexible + rigid with $\pm 5\%$ accidental torsion).

### 3.2 Diaphragm Aspect Ratio Limits (SDPWS Table 4.2.4)
- **Blocked Wood Structural Panel Diaphragm** (Table 4.2A / 4.2B):
  $$\frac{L}{W} \le 4.0$$
- **Unblocked Wood Structural Panel Diaphragm** (Table 4.2C):
  $$\frac{L}{W} \le 3.0$$

### 3.3 Framing Specific Gravity Adjustment Factor ($C_{sp}$)
- Tabulated nominal unit shears ($v_s, v_w$) in SDPWS Tables 4.2A and 4.2C are calibrated for Douglas Fir-Larch ($G = 0.50$) or Southern Pine ($G = 0.55$).
- For framing species with specific gravity $G < 0.50$ (per Footnote 2 of Tables 4.2A & 4.2C):
  $$C_{sp} = 1.0 - (0.50 - G) \le 1.00$$
  - **Spruce-Pine-Fir (SPF)** ($G = 0.42$): $C_{sp} = 1.0 - (0.50 - 0.42) = 0.92$.
  - **Hem-Fir (HF)** ($G = 0.43$): $C_{sp} = 1.0 - (0.50 - 0.43) = 0.93$.
  - **Douglas Fir-Larch (DF-L)** ($G = 0.50$) / **Southern Pine (SP)** ($G = 0.55$): $C_{sp} = 1.00$.

---

## 4. Step-by-Step Calculation Procedure (Dual ASD & LRFD)

### Step 1: Diaphragm Geometry & Aspect Ratio Check
1. Verify diaphragm span $L$ and width $W$ for both orthogonal lateral loading directions (North-South and East-West).
2. Calculate aspect ratio and compare against SDPWS Table 4.2.4:
   $$\text{Aspect Ratio} = \frac{L}{W} \le \begin{cases} 4.0 & \text{(Blocked WSP Diaphragm)} \\ 3.0 & \text{(Unblocked WSP Diaphragm)} \end{cases}$$

### Step 2: Diaphragm In-Plane Unit Shear Demand ($v_a, v_u$)
1. For a simply supported flexible diaphragm segment of span $L$ and depth $W$ subjected to uniform lateral load $w$ ($\text{plf}$):
   - Maximum Reaction Force at Boundary Line:
     $$V_{max} = \frac{w \cdot L}{2} \quad (\text{lbs})$$
   - Maximum In-Plane Unit Shear Demand at Boundary:
     $$v_{ASD} = \frac{V_{max,ASD}}{W} \quad (\text{plf}), \qquad v_{LRFD} = \frac{V_{max,LRFD}}{W} \quad (\text{plf})$$
2. Where diaphragm nailing is zoned (stepped down from high-shear boundaries toward midspan), determine the distance $x_{zone}$ from the support where unit shear drops below the next nailing zone capacity:
   $$v(x) = v_{max} \cdot \left(1 - \frac{2x}{L}\right)$$

### Step 3: Diaphragm Unit Shear Capacity ($v_{allow}, \phi v_n$)
1. Look up nominal unit shear capacity $v_s$ (Seismic) or $v_w$ (Wind) and apparent shear stiffness $G_a$ ($\text{kips/in.}$) from `SDPWS-2021_Table_4.2A_Blocked_Diaphragms.csv` (or `Table_4.2C` if unblocked).
2. Apply framing specific gravity factor $C_{sp}$ and resistance/safety factor (SDPWS Section 4.2.3):
   - **ASD Allowable Unit Shear**:
     $$v_{allow} = \frac{v_{nominal} \cdot C_{sp}}{\Omega} = \frac{v_{nominal} \cdot C_{sp}}{2.00} \quad (\text{plf})$$
   - **LRFD Factored Unit Shear Resistance**:
     $$\phi v_n = \phi_D \cdot v_{nominal} \cdot C_{sp} = 0.80 \cdot v_{nominal} \cdot C_{sp} \quad (\text{plf})$$
3. Verify Demand-to-Capacity Ratio:
   $$D/C_{shear} = \frac{v_{ASD}}{v_{allow}} \le 1.00 \quad \text{or} \quad \frac{v_{LRFD}}{\phi v_n} \le 1.00$$

### Step 4: Diaphragm In-Plane Deflection Check (SDPWS Eq. 4.2-1)
1. Compute the 3-component (formerly 4-term) midspan in-plane deflection $\delta_{dia}$ (in.) per SDPWS Section 4.2.2, Equation 4.2-1 ([WoodWorks Shear Wall & Diaphragm Guide](https://www.woodworks.org/wp-content/uploads/presentation_slides-STRASSER-Shearwalls-and-Diaphragms-WDS-200225.pdf)):
   $$\delta_{dia} = \underbrace{\frac{5 \cdot v \cdot L^3}{8 \cdot E \cdot A \cdot W}}_{\text{Chord Flexure}} + \underbrace{\frac{0.25 \cdot v \cdot L}{1000 \cdot G_a}}_{\text{Panel Shear + Nail Slip}} + \underbrace{\frac{\sum (\Delta_c \cdot x)}{2 \cdot W}}_{\text{Chord Splice Slip}} \quad (\text{in.})$$
   Where:
   - $v$ = Induced unit shear at the stage load level being evaluated ($\text{plf}$).
   - $L$ = Diaphragm length perpendicular to load ($\text{ft}$).
   - $W$ = Diaphragm width parallel to load ($\text{ft}$).
   - $E$ = Modulus of elasticity of diaphragm chords ($\text{psi}$).
   - $A$ = Cross-sectional area of chord framing member ($\text{in.}^2$).
   - $G_a$ = Apparent diaphragm shear stiffness from Table 4.2A or 4.2C ($\text{kips/in.}$).
   - $\Delta_c$ = Diaphragm chord splice slip ($\text{in.}$) at splice location $x$ ($\text{ft}$) from midspan (typically $\Delta_c \approx 0.03" \text{ to } 0.06"$ per nailed/bolted splice at ASD load, or $\Delta_c = 0$ for continuous unspliced headers/plates).
2. For multi-zone nailing across the diaphragm span, replace $v / G_a$ with the average value $\text{avg}(v_i / G_{a,i})$ weighted by zone length.

### Step 5: Diaphragm Chord Axial Tension & Compression Design
1. Calculate maximum diaphragm in-plane bending moment at midspan:
   $$M_{max} = \frac{w \cdot L^2}{8} \quad (\text{lb-ft})$$
2. Resolve into coupled axial chord force $T = C$ along the top plates, rim joists, or bond beams at the diaphragm perimeter (moment arm $= W$):
   $$T_{ASD} = C_{ASD} = \frac{M_{max,ASD}}{W} = \frac{w_{ASD} \cdot L^2}{8 \cdot W} \quad (\text{lbs})$$
   $$T_{LRFD} = C_{LRFD} = \frac{M_{max,LRFD}}{W} = \frac{w_{LRFD} \cdot L^2}{8 \cdot W} \quad (\text{lbs})$$
3. **Wood Top Plate Tension Member Check (NDS Section 3.8)**:
   - Check net section tension of continuous wood top plates at staggered splices:
     $$f_t = \frac{T}{A_{net}} \le F'_t = F_t \cdot C_D \cdot C_M \cdot C_t \cdot C_F \cdot C_i$$
4. **Chord Splice Connection Design (Lap Nails or Simpson Strap Ties)**:
   - At joints in double top plates or rim joists, transfer the chord tension force $T(x) = T_{max} \cdot \left[1 - \left(\frac{2x}{L}\right)^2\right]$ across the butt joint using either:
     - **Staggered Lap Nailing** between upper and lower top plates (e.g., $16\text{d}$ common nails $0.162" \times 3.5"$ with $Z' = Z \cdot C_D = 141 \times 1.60 = 225\text{ lbs/nail}$ in DF-L), checking wood net tension of the continuous plate, OR
     - **Simpson Strong-Tie Strap Tie** ([CS](https://www.strongtie.com/coiledstraps_specialtystraps/cs_strap/p/cs), [CMST](https://www.strongtie.com/coiledstraps_specialtystraps/cmst_strap/p/cmst), [LSTA](https://www.strongtie.com/straightstraps_strapsandties/lsta_strap/p/lsta), [MSTA](https://www.strongtie.com/straightstraps_strapsandties/msta_strap/p/msta), [MSTC](https://www.strongtie.com/straightstraps_strapsandties/mstc_strap/p/mstc), [MST](https://www.strongtie.com/straightstraps_strapsandties/mst_strap/p/mst)) from `Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv` such that:
       $$T_{ASD} \le T_{allow,Simpson} \quad (C_D = 1.60)$$

### Step 6: Collector (Drag Strut) Axial Force Profile & Connection Design
1. Where a shear wall segment of length $b_s$ does not extend the full diaphragm depth $W$, a collector (drag strut) must collect unit shear from the unsupported diaphragm width $(W - b_s)$ and deliver it into the shear wall.
2. Construct the axial force diagram along the line of the shear wall:
   - Unit diaphragm shear entering the collector line:
     $$v_{dia} = \frac{R_{line}}{W} \quad (\text{plf})$$
   - Unit shear resisting force inside the shear wall segment:
     $$v_{wall} = \frac{R_{line}}{b_s} \quad (\text{plf})$$
   - Net peak collector axial force at the end of the shear wall segment (for a wall starting at distance $x_1$ from diaphragm edge):
     $$F_{drag,max} = v_{dia} \cdot L_{unsupported} \quad (\text{lbs})$$
3. **Seismic Overstrength Amplification (ASCE 7-22 Section 12.10.2.1)**:
   - For structures assigned to **Seismic Design Category (SDC) C, D, E, or F**, collector elements, splices, and their connections to vertical resisting elements shall be designed for the seismic load effects including overstrength ($\Omega_0 E_h$, where $\Omega_0 = 2.5$ or $3.0$), **EXCEPT** in structures braced entirely by **light-frame shear walls** (ASCE 7-22 Section 12.10.2.1 Exception), where standard $1.0E$ (LRFD) / $0.7E$ (ASD) forces govern.
4. Select a Simpson strap tie (`MSTA`, `MSTC`, `MST`, `CMST`) or bolted splice to transfer $F_{drag,max}$ directly into the shear wall top plate/header.

### Step 7: Diaphragm-to-Shear-Wall Boundary Shear Transfer (LTP4 / LTP5 / A35 / Blocking)
1. Transfer unit shear $v_{max}$ ($\text{plf}$) from the roof/floor diaphragm sheathing through the rim joist or blocking into the wall top plate:
   - Select **Simpson [LTP4 / LTP5](https://www.strongtie.com/framinganglesandplates_anglesandplates/ltp_plate/p/ltp)** or **[A35](https://www.strongtie.com/framinganglesandplates_anglesandplates/a35_angle/p/a35)** framing angles spaced at:
     $$s_{clip} = \frac{F_{allow,clip} \cdot C_{sheathing}}{v_{ASD}} \cdot 12 \quad (\text{in. o.c.})$$
   - **Critical Sheathing Reduction Check**: When `LTP4` is installed over $3/8"$ or $1/2"$ wood structural panel sheathing using $1\text{-}1/2"$ nails, multiply allowable load by $C_{sheathing} = 0.72$ ($3/8"$) or $0.64$ ($1/2"$), OR specify $2\text{-}1/2"$ nails (`0.148" x 2.5"`) / `#9 x 2.5"` `SD9212` screws to maintain $100\%$ ($1.00\times$) capacity.

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State / Component | Demand Symbol | Capacity Symbol | Governing Code / Catalog Reference | Acceptance Criterion |
| :--- | :--- | :--- | :--- | :--- |
| **Diaphragm Aspect Ratio** | $L / W$ | $(L / W)_{max}$ | SDPWS Table 4.2.4 ($4:1$ Blocked, $3:1$ Unblocked) | $(L/W) / (L/W)_{max} \le 1.00$ |
| **In-Plane Unit Shear (ASD)** | $v_{ASD}$ ($\text{plf}$) | $v_{allow} = 0.50 \cdot v_{nom} \cdot C_{sp}$ | SDPWS Sec. 4.2.3 & Table 4.2A / 4.2C | $v_{ASD} / v_{allow} \le 1.00$ |
| **In-Plane Unit Shear (LRFD)** | $v_{LRFD}$ ($\text{plf}$) | $\phi v_n = 0.80 \cdot v_{nom} \cdot C_{sp}$ | SDPWS Sec. 4.2.3 & Table 4.2A / 4.2C | $v_{LRFD} / (\phi v_n) \le 1.00$ |
| **Diaphragm Midspan Deflection** | $\delta_{dia}$ ($\text{in.}$) | $\delta_{limit}$ (Wall out-of-plane drift limit) | SDPWS Eq. 4.2-1 & ASCE 7-22 Sec. 12.12 | $\delta_{dia} / \delta_{limit} \le 1.00$ |
| **Chord Member Net Tension** | $T_{ASD}$ ($\text{lbs}$) | $F'_t \cdot A_{net}$ ($\text{lbs}$) | NDS-2024 Sec. 3.8 | $T_{ASD} / (F'_t A_{net}) \le 1.00$ |
| **Chord / Collector Strap Tie** | $T_{ASD}$ or $F_{drag}$ ($\text{lbs}$) | $T_{allow,Simpson}$ ($\text{lbs}$) | Simpson C-C-2026 (`LSTA`/`MSTA`/`MSTC`/`MST`/`CS`/`CMST`) | $T_{ASD} / T_{allow,Simpson} \le 1.00$ |
| **Boundary Shear Clip Spacing** | $v_{ASD}$ ($\text{plf}$) | $F_{allow,clip} \cdot C_{sheath} / s_{clip}$ | Simpson C-C-2026 (`LTP4`/`LTP5`/`A35`/Blocking) | $v_{ASD} / v_{allow,transfer} \le 1.00$ |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **3x Framing at High-Shear Boundaries (SDPWS Table 4.2A Footnote 3)**:
   - Whenever `10d` common nails are spaced at $2\text{-}1/2"$ o.c. or $2"$ o.c. at diaphragm boundaries or continuous panel joints, **minimum $3\text{x}$ ($2.5"$ actual width) framing** is mandatory at adjoining panel edges and boundaries to prevent wood splitting. Plan checkers routinely reject $2\text{x}$ framing specified with `10d @ 2"` or `2.5" o.c.`.
2. **Coiled Strap Cut Length & Lap Splice Errors ([CS](https://www.strongtie.com/coiledstraps_specialtystraps/cs_strap/p/cs) / [CMST](https://www.strongtie.com/coiledstraps_specialtystraps/cmst_strap/p/cmst))**:
   - Coiled straps (`CS14`–`CS22`, `CMST12`–`CMST14`) require a minimum end length $L_{end}$ on **each side** of the joint or clear span: $L_{total} = \text{Clear Span} + 2 \cdot L_{end}$.
   - Never specify fewer nails than tabulated without linearly reducing the fastener-controlled capacity, and always place exactly $50\%$ of the total fasteners on each side of the splice joint.
3. **Cross-Grain Tension Prohibition (SDPWS Section 4.1.5 / NDS Section 4.1.4)**:
   - Diaphragm out-of-plane wall anchorage forces ($F_p$ for concrete/masonry walls per ASCE 7 Section 12.11.2) **shall never** be resisted by toe-nails or nails subject to withdrawal, nor by wood ledgers in cross-grain bending or cross-grain tension. Positive sub-diaphragm ties (`HDU`/`DTT`/`PGT`/`BPH`) anchored into framing members must be detailed.
4. **LTP4 Installed Over Sheathing ([Simpson LTP Page](https://www.strongtie.com/framinganglesandplates_anglesandplates/ltp_plate/p/ltp))**:
   - Standard `LTP4` uses $1.5"$ nails (`0.148" x 1.5"`). If installed on the exterior over $3/8"$ or $1/2"$ structural sheathing without lengthening the nails to $2.5"$ (`0.148" x 2.5"` or `SD9212`), capacity drops to $0.72\times$ or $0.64\times$. Always call out either direct-to-framing installation or $2.5"$ fasteners over sheathing.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Design a blocked single-story commercial wood roof diaphragm and its chord/collector connections:
- **Diaphragm Dimensions**: Span $L = 72\text{ ft}$ (East-West), Depth $W = 30\text{ ft}$ (North-South).
- **Framing & Sheathing**: Douglas Fir-Larch ($G = 0.50$, $E = 1,600,000\text{ psi}$) rafters/blocking (`2x` framing at interior, `2x6` double top plates $A = 2 \times 8.25 = 16.5\text{ in.}^2$). Sheathing is $15/32"$ `Sheathing` grade OSB panels with `10d` common nails (`3" x 0.148"`).
- **Governing Lateral Loads (Seismic Controls)**:
  - Factored LRFD Seismic Load: $w_{LRFD} = 450\text{ plf}$ ($1.0E$).
  - Allowable ASD Seismic Load: $w_{ASD} = 0.7 \times 450 = 315\text{ plf}$ ($0.7E$).
- **North Grid Line Collector**: The East wall is a $15\text{ ft}$ long shear wall segment located at the South end of the $30\text{ ft}$ line, requiring a $15\text{ ft}$ collector (drag strut) along the North half.

### 7.2 Step-by-Step Solution

#### 1. Aspect Ratio Check
$$\frac{L}{W} = \frac{72\text{ ft}}{30\text{ ft}} = 2.40 \le 4.00 \quad (\text{SDPWS Table 4.2.4 Blocked WSP}) \implies \textbf{OK}$$

#### 2. Diaphragm Unit Shear Demand
- Maximum Boundary Reaction:
  $$V_{ASD} = \frac{315 \times 72}{2} = 11,340\text{ lbs}, \qquad V_{LRFD} = \frac{450 \times 72}{2} = 16,200\text{ lbs}$$
- Maximum Boundary Unit Shear:
  $$v_{ASD} = \frac{11,340}{30} = 378.0\text{ plf}, \qquad v_{LRFD} = \frac{16,200}{30} = 540.0\text{ plf}$$

#### 3. Blocked Diaphragm Nailing Selection (`SDPWS-2021_Table_4.2A_Blocked_Diaphragms.csv`)
- For `Sheathing and Single-Floor`, `10d` common nails ($1\text{-}1/2"$ penetration), $15/32"$ OSB panel, $2"$ nominal framing ($C_{sp} = 1.00$ for DF-L):
  - **Zone 1 (Ends)**: Try `4 in. boundary / 6 in. other edges` (`10d @ 4"/6"/12"`):
    - Nominal Seismic Capacity: $v_s = 770\text{ plf}$, Apparent Stiffness $G_a = 15.0\text{ kips/in.}$ (OSB).
    - ASD Allowable Shear: $v_{allow} = 770 / 2.00 = 385.0\text{ plf} \ge 378.0\text{ plf} \quad (D/C = 0.982 \le 1.00) \implies \textbf{OK}$.
    - LRFD Factored Resistance: $\phi v_n = 0.80 \times 770 = 616.0\text{ plf} \ge 540.0\text{ plf} \quad (D/C = 0.877 \le 1.00) \implies \textbf{OK}$.
  - **Zone 2 (Interior)**: Try `6 in. boundary / 6 in. other edges` (`10d @ 6"/6"/12"`):
    - Nominal Seismic Capacity: $v_s = 580\text{ plf}$, $G_a = 25.0\text{ kips/in.}$ (OSB).
    - ASD Allowable Shear: $v_{allow,2} = 580 / 2.00 = 290.0\text{ plf}$.
    - Distance from support where $v_{ASD}(x) \le 290.0\text{ plf}$:
      $$x_{zone} = \frac{L}{2} \cdot \left(1 - \frac{290.0}{378.0}\right) = 36 \times (1 - 0.7672) = 8.38\text{ ft} \implies \text{Use Zone 1 for } 9\text{ ft at each end.}$$

#### 4. Diaphragm Midspan Deflection (SDPWS Eq. 4.2-1)
- Assuming 4 chord splices per side at $x = 10\text{ ft}$ and $22\text{ ft}$ from midspan with $\Delta_c = 0.03\text{ in.}$ each ($\sum \Delta_c x = 2 \times 2 \times 0.03 \times (10 + 22) = 3.84\text{ in.-ft}$), and conservative $G_a = 15.0\text{ kips/in.}$:
  $$\delta_{dia,ASD} = \frac{5 \times 378.0 \times 72^3}{8 \times 1,600,000 \times 16.5 \times 30} + \frac{0.25 \times 378.0 \times 72}{1000 \times 15.0} + \frac{3.84}{2 \times 30}$$
  $$\delta_{dia,ASD} = 0.1112 + 0.4536 + 0.0640 = 0.629\text{ in.}$$

#### 5. Chord Tension & Simpson Strap Selection
- Maximum Chord Force at Midspan:
  $$M_{ASD} = \frac{315 \times 72^2}{8} = 204,120\text{ lb-ft} \implies T_{ASD} = \frac{204,120}{30} = 6,804\text{ lbs}$$
- At splice location $x = 18\text{ ft}$ from midspan (quarter-point):
  $$T_{ASD}(18\text{ ft}) = 6,804 \times \left[1 - \left(\frac{2 \times 18}{72}\right)^2\right] = 6,804 \times 0.75 = 5,103\text{ lbs}$$
  - Select **Simpson [MST48](https://www.strongtie.com/straightstraps_strapsandties/mst_strap/p/mst)** (`12 ga`, $2\text{-}1/16" \times 48"$) with `(50) SD10112` screws (`25` per side) in DF-L:
    $$T_{allow,MST48} = 5,310\text{ lbs} \ge 5,103\text{ lbs} \quad (D/C = 0.961 \le 1.00) \implies \textbf{OK}$$

#### 6. Collector (Drag Strut) Strap Selection at East Line
- Total ASD reaction on East Line: $R_{ASD} = 11,340\text{ lbs}$; Shear wall length $b_s = 15\text{ ft}$, unsupported collector length $= 15\text{ ft}$.
- Collector axial tension/compression entering the North end of the $15\text{ ft}$ shear wall:
  $$F_{drag,ASD} = v_{ASD} \times 15\text{ ft} = 378.0 \times 15 = 5,670\text{ lbs}$$
- Select **Simpson [MSTC66](https://www.strongtie.com/straightstraps_strapsandties/mstc_strap/p/mstc)** (`14 ga`, $3" \times 65\text{-}3/4"$) with `(44) SD9112` screws (`22` per side) in DF-L:
  $$T_{allow,MSTC66} = 5,850\text{ lbs} \ge 5,670\text{ lbs} \quad (D/C = 0.969 \le 1.00) \implies \textbf{OK}$$
