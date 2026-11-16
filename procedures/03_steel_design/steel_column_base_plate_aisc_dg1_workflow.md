# Steel Column Base Plate & Anchor Rod Design Procedure (AISC 360-22 Sec. J8 / Design Guide 1)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Section J8 (Column Bases and Bearing on Concrete), Section J3 (Anchor Rods), and Section J2 (Column-to-Base-Plate Welds).
  - **AISC Steel Design Guide No. 1 (2nd Edition)**: *Base Plate and Anchor Rod Design* (Concentric Compression, Tension/Uplift, Small & Large Eccentricity Bending, Shear Transfer).
  - **ACI 318-19 / ACI 318-25**: Chapter 17 (Anchoring to Concrete — Concrete Breakout, Pullout, Side-Face Blowout) & Section 22.8 (Bearing Strength).
  - **OSHA 29 CFR 1926.755**: Steel Erection Standard (4-Bolt Minimum Rule & Erection Stability).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J3.2_Bolt_Strength.csv`
- **Design Philosophies (Dual LRFD & ASD)**:
  - **Concrete Bearing (AISC Sec. J8)**: $\phi_c = 0.65$ (LRFD), $\Omega_c = 2.31$ (ASD).
  - **Base Plate Flexural Yielding**: $\phi_b = 0.90$ (LRFD), $\Omega_b = 1.67$ (ASD).
  - **Anchor Rod Tension/Shear**: $\phi = 0.75$ (LRFD), $\Omega = 2.00$ (ASD).

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $P_u, M_u, V_u$ | Factored LRFD column base reactions (or $P_a, M_a, V_a$ ASD) | $\text{kips}, \text{kip-in.}$ | Frame Analysis (Base Fixity Model) |
| $d, b_f$ | Column section depth and flange width (or $H, B$ for HSS) | $\text{in.}$ | AISC 16th Ed. Shapes Database |
| $B, N$ | Base plate width ($B$, parallel to $b_f$) and length ($N$, parallel to $d$) | $\text{in.}$ | Base Plate Layout |
| $t_p, F_y$ | Base plate thickness and yield stress (typically ASTM A36, $F_y = 36\text{ ksi}$) | $\text{in.}, \text{ksi}$ | ASTM A36 / A572 Gr. 50 |
| $f'_c, A_2$ | Concrete pedestal/footing compressive strength and supporting area | $\text{ksi}, \text{in.}^2$ | Foundation Plan |
| $d_a, n_{rods}, \text{Grade}$ | Anchor rod diameter, quantity, and ASTM F1554 Grade (`36`, `55`, `105`) | $\text{in.}$ | `AISC_DG1_Base_Plate_...csv` |
| $f$ | Distance from column centerline to tension anchor rod centerline | $\text{in.}$ | Base Plate Anchor Layout |

---

## 3. Bearing Stress & Cantilever Projection Mechanics (AISC DG1)

### 3.1 Concrete Bearing Strength (AISC Sec. J8, Eq. J8-2)
- Maximum nominal bearing stress on concrete area $A_1 = B \cdot N$:
  $$P_p = 0.85 \cdot f'_c \cdot A_1 \cdot \sqrt{\frac{A_2}{A_1}} \le 1.7 \cdot f'_c \cdot A_1$$
- Maximum allowable / design bearing stress $f_{p,max}$:
  - **LRFD**: $f_{p(max),LRFD} = \phi_c \cdot 0.85 f'_c \sqrt{\frac{A_2}{A_1}} \le 0.65 (1.7 f'_c) = 1.105 f'_c$
  - **ASD**: $f_{p(max),ASD} = \frac{0.85 f'_c}{\Omega_c} \sqrt{\frac{A_2}{A_1}} \le \frac{1.7 f'_c}{2.31} = 0.736 f'_c$
  *(Note: Take $\sqrt{A_2 / A_1} \le 2.0$, where $A_2$ is the maximum geometrically similar area of concrete support).*

### 3.2 Base Plate Cantilever Bending Distances ($m, n, \lambda n'$)
- **For Wide-Flange Columns ($d, b_f$)**:
  $$m = \frac{N - 0.95 d}{2}, \qquad n = \frac{B - 0.80 b_f}{2}, \qquad n' = \frac{\sqrt{d \cdot b_f}}{4}$$
  $$\lambda = \frac{2 \sqrt{X}}{1 + \sqrt{1 - X}} \le 1.0, \quad \text{where } X = \left[\frac{4 d b_f}{(d + b_f)^2}\right] \frac{P_u}{\phi_c P_p} \; (\text{conservatively } \lambda = 1.0)$$
- **For HSS Rectangular/Square Columns ($H, B_{hss}$)**:
  $$m = \frac{N - 0.95 H}{2}, \qquad n = \frac{B - 0.95 B_{hss}}{2}$$
- **Governing Cantilever Arm**: $l = \max(m, \; n, \; \lambda n')$.

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Select Base Plate Plan Dimensions ($B \times N$)
1. Ensure $B$ and $N$ accommodate the column footprint plus anchor rod holes (`AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv`) and edge distances ($\ge 1.25 d_a$ to $1.5 d_a$ from rod centerline to plate edge).
2. For pure axial compression ($M = 0$): Verify $A_1 = B \cdot N \ge A_{1,req} = \frac{P_u}{f_{p(max),LRFD}}$ (or $\frac{P_a}{f_{p(max),ASD}}$).

### Step 2: Combined Axial Compression + Bending Moment (Eccentricity $e = M / P$)
Compute critical eccentricity $e_{crit} = \frac{N}{2} - \frac{P}{2 q_{max}}$, where $q_{max} = f_{p,max} \cdot B$ ($\text{kips/in.}$):
- **Case A — Small Eccentricity ($e \le e_{crit}$, No Anchor Rod Tension)**:
  - Bearing length: $Y = N - 2 e$
  - Uniform bearing stress over $B \times Y$: $f_p = \frac{P}{B \cdot Y} \le f_{p,max}$
  - Required plate thickness on compression cantilever $l = \max(m, n)$:
    - If $Y \ge l$: $t_{p,req} = \sqrt{\frac{2 f_p l^2}{0.90 F_y}}$ (LRFD) or $\sqrt{\frac{3.33 f_p l^2}{F_y}}$ (ASD)
    - If $Y < l$: $t_{p,req} = \sqrt{\frac{2 f_p Y (2l - Y)}{0.90 F_y}}$ (LRFD)
- **Case B — Large Eccentricity ($e > e_{crit}$, Tension in Anchor Rods)**:
  - Check feasibility: $(f + N/2)^2 \ge \frac{2 P (e + f)}{q_{max}}$. If not, increase $B$ or $N$.
  - Bearing length $Y$ (solving quadratic equilibrium):
    $$Y = \left(f + \frac{N}{2}\right) - \sqrt{\left(f + \frac{N}{2}\right)^2 - \frac{2 P (e + f)}{q_{max}}}$$
  - Anchor rod total tension force:
    $$T = q_{max} \cdot Y - P \quad (\text{kips})$$
  - Required plate thickness at **compression side** ($t_{p,comp}$ using $q_{max}$ over $Y$) AND **tension side** (anchor rod bending at distance $x = f - 0.5(0.95d)$ from column flange):
    $$t_{p,tens} = \sqrt{\frac{4 \cdot T \cdot x}{0.90 \cdot B_{eff} \cdot F_y}} \quad (\text{LRFD}) \quad \text{or} \quad \sqrt{\frac{4 \cdot 1.67 \cdot T \cdot x}{B_{eff} \cdot F_y}} \quad (\text{ASD})$$
    *(Where $B_{eff}$ is the effective bending width across the tension anchor rods, typically $2x$ per rod or $B$).*

### Step 3: Anchor Rod Tension & Concrete Anchorage (AISC DG1 & ACI 318 Ch. 17)
1. **Anchor Rod Steel Tensile Strength** (`AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv`):
   $$T_{rod} = \frac{T}{n_{t}} \le \phi R_{nt} = 0.75 (0.75 F_u) A_b \; (\text{LRFD}) \;\text{or}\; \frac{R_{nt}}{\Omega} = 0.375 F_u A_b \; (\text{ASD})$$
2. **Concrete Breakout, Pullout & Side-Face Blowout**: Verify embedment depth $h_{ef}$ and edge distance $c_{a1}$ per **ACI 318-19 Chapter 17** (`N_cb`, `N_pn`, `N_sb`).

### Step 4: Base Shear Transfer ($V_u, V_a$)
Per AISC Design Guide 1 Section 3.5, transfer column base shear using one of three mechanisms:
1. **Concrete-to-Plate Friction** (only where net compression $P_{min}$ exists): $V_f = \mu \cdot P_{min}$ ($\mu = 0.55$ grout, $0.70$ concrete, $\phi = 0.75 / \Omega = 2.00$).
2. **Anchor Rod Shear** (requires **welded plate washers** over oversized base plate holes per DG1): Check $V_{rod} \le \phi F_{nv} A_b$ (and combined shear-tension per AISC Sec. J3.7).
3. **Embedded Shear Lug** (for high base shear): Design plate lug bearing against concrete ($\phi 0.85 f'_c A_{lug}$) and concrete shear breakout.

### Step 5: Column-to-Base-Plate Weld & OSHA Erection Check
- Size fillet welds (or PJP/CJP) around column flanges/web per AISC Sec. J2 to transfer net uplift $T$, bending moment $M$, and base shear $V$.
- **OSHA 29 CFR 1926.755**: Provide minimum **4 anchor rods** and verify base plate/anchors resist $300\text{ lb}$ at $18\text{ in.}$ eccentricity during erection.

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State | Demand | LRFD Capacity ($\phi R_n$) | ASD Capacity ($R_n / \Omega$) | Code Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Concrete Bearing** | $f_p$ ($\text{ksi}$) | $0.65 (0.85 f'_c \sqrt{A_2/A_1}) \le 1.105 f'_c$ | $0.368 f'_c \sqrt{A_2/A_1} \le 0.736 f'_c$ | AISC Sec. J8, Eq. J8-2 |
| **Base Plate Flexure (Comp.)** | $t_{p,req}$ | $t_p \ge t_{p,comp}$ ($\phi_b = 0.90$) | $t_p \ge t_{p,comp}$ ($\Omega_b = 1.67$) | AISC DG1 Sec. 3.1–3.3 |
| **Base Plate Flexure (Tens.)** | $t_{p,req}$ | $t_p \ge t_{p,tens}$ ($\phi_b = 0.90$) | $t_p \ge t_{p,tens}$ ($\Omega_b = 1.67$) | AISC DG1 Sec. 3.2–3.3 |
| **Anchor Rod Steel Tension** | $T / n_t$ | $0.5625 F_u A_b$ | $0.375 F_u A_b$ | AISC Table J3.2 & DG1 |
| **Anchor Concrete Breakout** | $N_{ua}$ | $\phi N_{cb}$ (ACI 318 Ch. 17) | $\phi N_{cb} / 1.43$ (approx.) | ACI 318-19 Sec. 17.6.2 |
| **Base Shear Transfer** | $V$ | $\phi V_n$ (Friction / Lug / Rods) | $V_n / \Omega$ (Friction / Lug / Rods) | AISC DG1 Sec. 3.5 |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Oversized Base Plate Holes & Plate Washers (`AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv`)**:
   - Standard steel bolt holes ($d + 1/16"$) are **too tight** for concrete anchor rods! Specify AISC DG1 oversized holes (e.g. $1\text{-}5/16"$ for $3/4"$ rod; $1\text{-}13/16"$ for $1"$ rod) with heavy square plate washers (`2.5"x2.5"x5/16"` or `3"x3"x3/8"`).
   - **Shear Transfer Note**: If anchor rods are relied upon to resist base shear, **plate washers must be shop- or field-welded to the top of the base plate** (unless a shear lug or friction carries 100% of shear).
2. **Minimum 4 Anchor Rods (OSHA Mandate)**:
   - Even for pinned-base gravity columns with zero moment, OSHA 29 CFR 1926.755 requires a minimum of **4 anchor rods** (except small post-type columns $< 300\text{ lbs}$).
3. **Non-Shrink Grout Pad**:
   - Detail a minimum $1\text{ in.}$ to $1\text{-}1/2\text{ in.}$ non-shrink grout pad ($f'_{c,grout} \ge 2 \cdot f'_c$ or $\ge 5,000\text{ psi}$) beneath the base plate, with a grout hole if $B$ or $N > 24\text{ in.}$.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Design a base plate and anchor rod assembly for a **`W10x49` ASTM A992 column** ($d = 10.0\text{ in.}, b_f = 10.0\text{ in.}$) supported on a large concrete footing ($f'_c = 4.0\text{ ksi}$, $\sqrt{A_2/A_1} = 2.0$) subjected to combined compression and major-axis bending:
- **Applied LRFD Loads**: $P_u = 120.0\text{ kips}$, $M_u = 900.0\text{ kip-in.}$ ($75.0\text{ kip-ft}$), $V_u = 12.0\text{ kips}$.
- **Applied ASD Loads**: $P_a = 80.0\text{ kips}$, $M_a = 600.0\text{ kip-in.}$ ($50.0\text{ kip-ft}$), $V_a = 8.0\text{ kips}$.
- **Trial Base Plate**: $B = 16.0\text{ in.}, N = 16.0\text{ in.}$, ASTM A36 ($F_y = 36\text{ ksi}$), with **(4) `1"` dia. ASTM F1554 Gr. 36** anchor rods ($2$ per side at $f = 6.25\text{ in.}$ from centerline).

### 7.2 Step-by-Step Solution (LRFD)

#### 1. Concrete Bearing Capacity & Critical Eccentricity
- Maximum LRFD concrete bearing stress ($\sqrt{A_2/A_1} = 2.0$):
  $$f_{p(max)} = 0.65 \times 0.85 \times 4.0 \times 2.0 = 4.42\text{ ksi}$$
  $$q_{max} = 4.42 \times 16.0 = 70.72\text{ kips/in.}$$
- Eccentricity & Critical Eccentricity:
  $$e = \frac{M_u}{P_u} = \frac{900.0}{120.0} = 7.50\text{ in.}$$
  $$e_{crit} = \frac{16.0}{2} - \frac{120.0}{2 \times 70.72} = 8.00 - 0.848 = 7.152\text{ in.}$$
  Since $e = 7.50\text{ in.} > e_{crit} = 7.152\text{ in.}$, **Case B (Large Eccentricity — Tension in Anchor Rods)** governs!

#### 2. Bearing Length ($Y$) & Anchor Tension ($T_u$)
- Check feasibility: $(f + N/2)^2 = (6.25 + 8.0)^2 = 203.06 \ge \frac{2(120)(7.50 + 6.25)}{70.72} = 46.66 \implies \textbf{OK}$.
- Bearing length $Y$:
  $$Y = 14.25 - \sqrt{203.06 - 46.66} = 14.25 - 12.506 = 1.744\text{ in.}$$
- Total tension in the 2 tension-side anchor rods:
  $$T_u = q_{max} Y - P_u = 70.72(1.744) - 120.0 = 123.34 - 120.0 = 3.34\text{ kips}$$
- Tension per anchor rod ($2$ rods): $T_{rod} = 3.34 / 2 = 1.67\text{ kips} \ll \phi R_{nt} = 25.61\text{ kips}$ (`AISC_DG1_...csv` for `1"` F1554 Gr. 36) $\implies \textbf{OK}$.

#### 3. Required Base Plate Thickness ($t_p$)
- Cantilever projection $m = (16.0 - 0.95 \times 10.0)/2 = 3.25\text{ in.}$; $n = (16.0 - 0.80 \times 10.0)/2 = 4.00\text{ in.}$
- Compression side ($Y = 1.744" < m = 3.25"$):
  $$t_{p,comp} = \sqrt{\frac{2 \times 4.42 \times 1.744 \times (2 \times 3.25 - 1.744)}{0.90 \times 36}} = \sqrt{\frac{73.32}{32.40}} = 1.504\text{ in.}$$
- Tension side ($x = 6.25 - 0.5 \times 0.95 \times 10.0 = 1.50\text{ in.}$, $B_{eff} = 16.0\text{ in.}$):
  $$t_{p,tens} = \sqrt{\frac{4 \times 3.34 \times 1.50}{0.90 \times 16.0 \times 36}} = 0.197\text{ in.}$$
- **Select `1-5/8"` (1.625 in.) x `16"` x `16"` ASTM A36 Base Plate** (or increase $N$ to $18\text{ in.}$ to reduce $t_p$).

#### 4. Base Shear Transfer Check ($V_u = 12.0\text{ kips}$)
- Friction resistance ($\mu = 0.55$ on grout, $P_{min} = 120.0\text{ kips}$):
  $$\phi V_f = 0.75 \times 0.55 \times 120.0 = 49.50\text{ kips} \ge 12.0\text{ kips} \quad (D/C = 0.242) \implies \textbf{OK}$$
- Provide `1-13/16"` oversized holes in base plate with `3" x 3" x 3/8"` plate washers per `AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv`.
