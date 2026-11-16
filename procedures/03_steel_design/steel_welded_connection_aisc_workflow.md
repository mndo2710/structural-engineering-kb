# Structural Steel Welded Connection Design Procedure (ANSI/AISC 360-22 Section J2)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Chapter J, Section J2 (Welds: Tables J2.1–J2.5) & Section J4 (Affected Elements).
  - **AISC Steel Construction Manual, 16th Edition**: Part 8 (Design Considerations for Welds — Elastic & Instantaneous Center of Rotation Methods).
  - **AWS D1.1/D1.1M**: *Structural Welding Code—Steel* (Prequalified Joint Details, Matching Filler Metals, Inspection).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.4.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.5_Welded_Joints.csv`
- **Design Philosophies (Dual LRFD & ASD)**:
  - **Fillet & PJP Shear**: $\phi = 0.75$ (LRFD), $\Omega = 2.00$ (ASD).
  - **PJP Tension Normal to Weld Axis**: $\phi = 0.80, \Omega = 1.88$ (Weld) and $\phi = 0.75, \Omega = 2.00$ (Base Metal).
  - **CJP Groove Welds**: Governed by base metal strength when matching filler metal is used (no separate weld check required).

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $P_u, V_u, M_u$ | Factored LRFD demands (or $P_a, V_a, M_a$ ASD demands) at weld group | $\text{kips}, \text{kip-in.}$ | Structural Analysis |
| $F_{EXX}$ | Electrode classification tensile strength (`70 ksi` for E70XX, `80 ksi` for E80XX) | $\text{ksi}$ | AWS D1.1 / AISC Table J2.5 |
| $t_{min}, t_{max}$ | Thickness of thinner and thicker parts joined | $\text{in.}$ | Member / Plate Schedule |
| $F_y, F_u$ | Base metal yield stress and ultimate tensile strength | $\text{ksi}$ | ASTM A36, A572 Gr. 50, A992, A500 Gr. C |
| $w$ | Fillet weld leg size (in $1/16\text{ in.}$ increments, $D = 16 w$) | $\text{in.}$ | AISC Sec. J2.2b & Table J2.4 |
| $l$ | Actual length of each weld segment | $\text{in.}$ | Connection Detailing |
| $\theta$ | Angle between longitudinal weld axis and resultant load vector | $\text{deg}$ | AISC Sec. J2.4(b) |

---

## 3. Sizing Limits & Effective Area Rules

### 3.1 Minimum & Maximum Fillet Weld Sizes (AISC Table J2.4 & Sec. J2.2b)
- **Minimum Size ($w_{min}$, Table J2.4)** — Based on **thinner** part joined (single-pass weld):
  - $t_{min} \le 1/4" \implies w_{min} = 1/8"$
  - $1/4" < t_{min} \le 1/2" \implies w_{min} = 3/16"$
  - $1/2" < t_{min} \le 3/4" \implies w_{min} = 1/4"$
  - $t_{min} > 3/4" \implies w_{min} = 5/16"$
- **Maximum Size ($w_{max}$, Sec. J2.2b)**:
  - Along edges of material $< 1/4"$ thick: $w_{max} = t$
  - Along edges of material $\ge 1/4"$ thick: $w_{max} = t - 1/16"$ (unless specifically designated to build out to full thickness).

### 3.2 Effective Length & Long-Weld Reduction ($eta$, AISC Sec. J2.2b)
- **Minimum Length**: $l_{min} \ge 4 w$ (otherwise effective size $w_{eff} = l / 4$). For longitudinal fillet welds alone in flat-bar tension connections, length of each weld $\ge$ perpendicular distance between them.
- **End-Loaded Fillet Welds ($l > 100w$)**: Multiply effective length by:
  $$\beta = 1.2 - 0.002 \left(\frac{l}{w}\right) \le 1.00 \quad (\text{for } 100 < l/w \le 300; \; \beta l_{eff} = 180 w \text{ if } l/w > 300)$$

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Fillet Weld Effective Throat & Nominal Strength (AISC Sec. J2.4)
1. **Effective Throat Thickness ($E$)**:
   - Equal-leg fillet weld: $E = 0.7071 \cdot w = \frac{\sqrt{2}}{2} w$
   - Flare-bevel groove weld (e.g. HSS corner or round bar): $E = \frac{5}{16} R$ (GMAW/FCAW) or $\frac{5}{32} d_b$ for round bar flush-filled (AISC Table J2.2).
2. **Effective Weld Area**: $A_{we} = E \cdot l_{eff}$.
3. **Weld Metal Nominal Strength ($F_{nw}$, Table J2.5 & Sec. J2.4(b))**:
   - Base nominal shear stress: $F_{nw} = 0.60 \cdot F_{EXX}$
   - With directional strength increase (permitted for non-HSS-end fillet welds):
     $$F_{nw} = 0.60 \cdot F_{EXX} \cdot \left(1.0 + 0.50 \sin^{1.5}\theta\right)$$
   - **Shortcut for E70XX ($F_{EXX} = 70\text{ ksi}$, $\theta = 0^\circ$)** per $1/16\text{ in.}$ weld leg ($D = 16 w$) per inch of weld:
     $$\phi r_n = 0.75 \times (0.60 \times 70) \times 0.7071 \times \frac{D}{16} = 1.392 \cdot D \; (\text{kips/in.}) \quad [\text{LRFD}]$$
     $$r_n / \Omega = \frac{(0.60 \times 70) \times 0.7071 \times (D/16)}{2.00} = 0.928 \cdot D \; (\text{kips/in.}) \quad [\text{ASD}]$$

### Step 2: Base Metal Strength at Fusion Face (AISC Table J2.5 & Sec. J4.2)
1. Although Table J2.5 relies on Sec. J4 for base metal capacity, verify the connected plate/flange shear capacity adjacent to the weld does not govern over the weld metal:
   - **Shear Yielding**: $R_{n,BM} = 0.60 F_y t l \quad (\phi = 1.00, \; \Omega = 1.50)$
   - **Shear Rupture**: $R_{n,BM} = 0.60 F_u t l \quad (\phi = 0.75, \; \Omega = 2.00)$
   - **Maximum Useful Fillet Weld Size (E70XX on A36/A992)**:
     - Single-sided weld on plate of thickness $t$ ($F_u = 65\text{ ksi}$): $w_{useful} = \frac{0.75 (0.60 F_u t)}{1.392 \times 16} \approx 1.31 t$; for double-sided welds on a web/plate of thickness $t$: $w_{useful,each} = \frac{0.60 F_u t}{2 \times 0.7071 \times 0.60 F_{EXX}} = \frac{0.707 F_u t}{F_{EXX}}$ (e.g., $w \le 0.66 t$ for $F_u=65, F_{EXX}=70$).

### Step 3: Eccentrically Loaded Weld Groups (In-Plane & Out-of-Plane)
1. **Elastic Vector Method (Conservative Standard)**:
   - Compute weld group centroid $(\bar{x}, \bar{y})$, total length $L_w$, and polar moment of inertia $I_p = I_x + I_y$ treating weld as unit-thickness line elements.
   - Direct shear per unit length: $f_v = \frac{V}{L_w}$
   - Moment shear components at extreme weld point $(x_{max}, y_{max})$ from centroid:
     $$f_{mx} = \frac{M \cdot y_{max}}{I_p}, \qquad f_{my} = \frac{M \cdot x_{max}}{I_p}$$
   - Resultant demand per inch of weld:
     $$f_r = \sqrt{(f_{vx} + f_{mx})^2 + (f_{vy} + f_{my})^2} \le \phi r_n \; [\text{LRFD}] \; \text{or} \; r_n / \Omega \; [\text{ASD}]$$
2. **Instantaneous Center of Rotation (IC) Method (AISC Manual Part 8)**:
   - Permitted for ultimate strength evaluation using load-deformation curve $R = R_{ult}(1 - e^{-10\Delta})^{0.55}$ and AISC Manual Tables 8-4 through 8-11 ($C$ coefficients: $R_n = C \cdot C_1 \cdot D \cdot l$).

### Step 4: PJP & CJP Groove Welds (AISC Table J2.5)
- **CJP Groove Welds**: Use matching filler metal; strength equals base metal.
- **PJP Groove Welds**: Effective throat $E$ per Table J2.1 (e.g. $S - 1/8"$ for SMAW/FCAW $45^\circ$ bevel). Check **both** weld metal ($0.60 F_{EXX}, \phi=0.80/\Omega=1.88$ tension; $\phi=0.75/\Omega=2.00$ shear) and base metal tension rupture ($F_u, \phi=0.75/\Omega=2.00$).

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State | Demand | LRFD Capacity ($\phi R_n$) | ASD Capacity ($R_n / \Omega$) | Code Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Min/Max Fillet Weld Size** | $w$ | $w_{min} \le w \le w_{max}$ | $w_{min} \le w \le w_{max}$ | AISC Table J2.4 & Sec. J2.2b |
| **Fillet Weld Shear (E70XX)** | $f_r$ ($\text{kips/in.}$) | $1.392 \cdot D \cdot (1+0.5\sin^{1.5}\theta)$ | $0.928 \cdot D \cdot (1+0.5\sin^{1.5}\theta)$ | AISC Table J2.5 & Sec. J2.4 |
| **Base Metal Shear Yielding** | $V$ ($\text{kips}$) | $1.00 (0.60 F_y t l)$ | $0.667 (0.60 F_y t l)$ | AISC Sec. J4.2, Eq. J4-3 |
| **Base Metal Shear Rupture** | $V$ ($\text{kips}$) | $0.75 (0.60 F_u t l)$ | $0.50 (0.60 F_u t l)$ | AISC Sec. J4.2, Eq. J4-4 |
| **PJP Tension (Normal to Weld)** | $T$ ($\text{kips}$) | $\min(0.80(0.60 F_{EXX} A_{we}), 0.75 F_u A_{BM})$ | $\min(0.532(0.60 F_{EXX} A_{we}), 0.50 F_u A_{BM})$ | AISC Table J2.5 |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **No Directional Strength Increase on Rectangular HSS Ends (AISC Sec. J2.4(b)(2))**:
   - Never apply the $(1.0 + 0.50 \sin^{1.5}\theta)$ factor to fillet welds connecting the end of a rectangular HSS to a cap plate or base plate.
2. **Minimum Fillet Weld Size Controlled by Thicker vs. Thinner Part**:
   - Table J2.4 depends on the **thinner** part joined (never exceed the thickness of the thinner part unless built up). Plan checkers often reject $1/4"$ welds on $3/16"$ HSS walls where $w_{max} = 3/16"$.
3. **End Returns / Boxing of Welds (AISC Sec. J2.2b)**:
   - Fillet welds on flexible shear tabs or angles subjected to cyclic/eccentric out-of-plane rotation must **not** be returned around the top corner if it inhibits end rotation, whereas brackets in-plane require returns $\ge 2 w$.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Size the fillet weld for an eccentrically loaded **`1/2"` ASTM A36 bracket plate** ($F_y = 36\text{ ksi}, F_u = 58\text{ ksi}$) welded to a `W12x65` column flange ($t_f = 0.605"$, A992) using a **C-shaped 3-sided weld group** (`5"` top horizontal + `10"` vertical + `5"` bottom horizontal) with **E70XX electrodes** ($F_{EXX} = 70\text{ ksi}$):
- **Vertical Load**: $V_u = 36.0\text{ kips}$ (LRFD), $V_a = 24.0\text{ kips}$ (ASD), acting downward at $e_0 = 8.0\text{ in.}$ from the vertical weld line.

### 7.2 Step-by-Step Solution (Elastic Vector Method)

#### 1. Weld Group Properties (Unit-Thickness Line Elements)
- Total weld length: $L_w = 5.0 + 10.0 + 5.0 = 20.0\text{ in.}$
- Centroid from vertical weld line:
  $$\bar{x} = \frac{2 \times (5.0 \times 2.5)}{20.0} = 1.25\text{ in.}, \qquad \bar{y} = 5.00\text{ in. (mid-height)}$$
- Moment of inertia about centroid:
  $$I_x = \frac{10.0^3}{12} + 2 \times (5.0 \times 5.0^2) = 83.33 + 250.0 = 333.33\text{ in.}^3$$
  $$I_y = 10.0(1.25)^2 + 2 \times \left[\frac{5.0^3}{12} + 5.0(2.5 - 1.25)^2\right] = 15.63 + 2(10.42 + 7.81) = 52.08\text{ in.}^3$$
  $$I_p = I_x + I_y = 333.33 + 52.08 = 385.42\text{ in.}^3$$

#### 2. Resultant Stress at Extreme Corner ($x = 5.0 - 1.25 = +3.75\text{ in.}, y = +5.00\text{ in.}$)
- Eccentricity from weld centroid: $e = 8.0 - 1.25 = 6.75\text{ in.}$
- **LRFD** ($V_u = 36.0\text{ kips}, M_u = 36.0 \times 6.75 = 243.0\text{ kip-in.}$):
  $$f_{vy} = \frac{36.0}{20.0} = 1.80\text{ kips/in.}$$
  $$f_{mx} = \frac{243.0 \times 5.00}{385.42} = 3.152\text{ kips/in.}, \qquad f_{my} = \frac{243.0 \times 3.75}{385.42} = 2.364\text{ kips/in.}$$
  $$f_{r,LRFD} = \sqrt{(3.152)^2 + (1.80 + 2.364)^2} = \sqrt{9.935 + 17.339} = 5.222\text{ kips/in.}$$
- **ASD** ($V_a = 24.0\text{ kips}, M_a = 24.0 \times 6.75 = 162.0\text{ kip-in.}$):
  $$f_{r,ASD} = 5.222 \times \left(\frac{24.0}{36.0}\right) = 3.481\text{ kips/in.}$$

#### 3. Required Fillet Weld Size ($D$ in $1/16\text{ in.}$)
- Using conservative base fillet weld strength ($	heta = 0^\circ$):
  - **LRFD**: $D_{req} = \frac{5.222}{1.392} = 3.75 \implies \text{Try } D = 4 \text{ (} 1/4" \text{ fillet weld)}$
    $$\phi r_n = 1.392 \times 4 = 5.568\text{ kips/in.} \ge 5.222\text{ kips/in.} \quad (D/C = 0.938 \le 1.00) \implies \textbf{OK}$$
  - **ASD**: $r_n / \Omega = 0.928 \times 4 = 3.712\text{ kips/in.} \ge 3.481\text{ kips/in.} \quad (D/C = 0.938 \le 1.00) \implies \textbf{OK}$
- **Table J2.4 & Sec. J2.2b Check**: Thinner part $t = 1/2" \implies w_{min} = 3/16"$ (Table J2.4), $w_{max} = 1/2" - 1/16" = 7/16"$. Provided $w = 1/4" \implies \textbf{OK}$.
