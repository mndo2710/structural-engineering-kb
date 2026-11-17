# Single-Plate Shear Connection (Shear Tab) Design Procedure (AISC 360-22 / Manual Part 10)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Section B3.4 (Simple Connections), Section J2 (Welds), Section J3 (Bolts), Section J4 (Connecting Elements), and Chapter K (Table K1.2 for HSS Column Support).
  - **AISC Steel Construction Manual, 16th Edition**: Part 10 (Single-Plate Shear Connections — Conventional Table 10-9, Extended Configurations & Single-Plate Connections to HSS), Part 7 (ICOR $C$-Coefficients), Part 9 (Plate Buckling & Coped Beams).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC_Manual_16th_Part10_Shear_Tab_and_Single_Angle_Design.csv`
  - `database/aisc_360/ch_j_connections/AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J3.2_Bolt_Strength.csv`
- **Design Philosophies (Dual LRFD & ASD)**:
  - **Simple Connection Ductility**: A shear tab must yield flexurally or elongate at bolt holes before bolt shear rupture or weld fracture occurs, allowing beam-end rotation under gravity loading.

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $V_u, V_a$ | Factored (LRFD) or Allowable (ASD) beam end shear reaction | $\text{kips}$ | Structural Analysis |
| $d_{beam}, t_w, T$ | Supported beam depth, web thickness, and $T$-dimension | $\text{in.}$ | AISC Shapes Database |
| $t_p, d_p, F_y, F_u$ | Shear tab plate thickness, depth ($d_p \ge T/2$), yield & tensile strength | $\text{in.}, \text{ksi}$ | ASTM A36 / A572 Gr. 50 |
| $a$ | Distance from support weld line to centerline of first vertical bolt row | $\text{in.}$ | Connection Detailing ($a \le 3.5"$ Conv.) |
| $n, d_b, s$ | Number of bolts ($n$), bolt diameter ($d_b$), vertical pitch ($s = 3.0"$) | $\text{in.}$ | `AISC360-22_Table_J3.2_Bolt_Strength.csv` |
| $L_{ev}, L_{eh}$ | Vertical edge distance ($L_{ev}$) and horizontal edge distance ($L_{eh}$) | $\text{in.}$ | Table J3.4 ($L_{eh} \ge 2.0 d_b$ Conv.) |
| $w$ | Double-sided fillet weld leg size connecting shear tab to support | $\text{in.}$ | `AISC360-22_Table_J2.4.csv` |

---

## 3. Conventional vs. Extended Configuration Classification (AISC Manual Part 10)
1. **Conventional Configuration (Table 10-9)**:
   - Single vertical row of $2$ to $12$ bolts (`STD` or `SSL` holes).
   - Distance from weld line to bolt line $a \le 3.5\text{ in.}$
   - Horizontal edge distance $L_{eh} \ge 2.0 \cdot d_b$ (on both plate and beam web).
   - Design eccentricity: $e = a / 2$ (for $n \le 9$); $e = a$ if $n > 9$.
   - Ductility plate thickness cap: $t_{p,max} = \frac{d_b}{2} + \frac{1}{16}\text{ in.}$
2. **Extended Configuration** (e.g., reaching past column flanges into column web):
   - Any shear tab with $a > 3.5\text{ in.}$, $\ge 2$ vertical rows of bolts, or $L_{eh} < 2.0 \cdot d_b$.
   - Design eccentricity: Full $e = a$ (from weld line to centroid of bolt group).
   - Ductility plate thickness cap: $t_{p,max} = \frac{6 M_{max}}{F_y d_p^2}$, where $M_{max} = \left(\frac{F_{nv}}{0.90}\right) A_b C'$.
   - Must additionally check **plate flexural yielding/rupture**, **von Mises shear-flexure interaction**, and **plate local buckling**.

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Geometric Detailing & Ductility Limits
1. Verify plate depth $d_p \ge 0.50 \cdot T_{beam}$ (stability against beam twist) and $d_p \le T_{beam}$ (clearance between beam fillets).
2. Verify bolt spacing $s \ge 2\frac{2}{3} d_b$ ($3.0"$ standard) and edge distances $L_{ev}, L_{eh} \ge l_{e,Table\,J3.4} + C_2$.
3. **Ductility Thickness Limit ($t_{p,max}$)**:
   - Conventional: $t_p \le \frac{d_b}{2} + \frac{1}{16}\text{ in.}$ (or check $t_{p,max} = \frac{6 M_{max}}{F_y d_p^2}$).
   - Extended: $t_p \le \frac{6 (F_{nv}/0.90) A_b C'}{F_y d_p^2}$ (using $C'$ from `AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv`).

### Step 2: Bolt Group Shear Capacity with Eccentricity (AISC Sec. J3.6 & Part 7)
1. Determine design eccentricity $e$ ($a/2$ Conventional; $a$ Extended).
2. Look up ICOR coefficient $C$ from `AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv` for $(n, e)$.
3. Compute bolt group shear capacity ($n_s = 1$ single shear):
   $$R_{n,bolts} = C \cdot F_{nv} \cdot A_b \qquad (\phi = 0.75 \; \text{LRFD}, \; \Omega = 2.00 \; \text{ASD})$$

### Step 3: Bolt Bearing & Tearout on Plate AND Beam Web (AISC Sec. J3.10)
1. Check **both** the shear tab plate ($t_p, F_{u,p}$) and the supported beam web ($t_w, F_{u,w}$):
   - Edge bolt: $l_{c,edge} = L_{ev} - d_h / 2$
   - Interior bolts: $l_{c,int} = s - d_h$
   $$r_{n,i} = \min(1.2 \cdot l_{c,i} \cdot t \cdot F_u,\;\; 2.4 \cdot d_b \cdot t \cdot F_u)$$
2. Effective group capacity accounting for eccentricity (AISC Manual Part 7):
   $$R_{n,brg} = \frac{C}{n} \sum_{i=1}^{n} \min\left(F_{nv} A_b,\;\; r_{n,plate,i},\;\; r_{n,web,i}\right) \qquad (\phi = 0.75, \; \Omega = 2.00)$$

### Step 4: Shear Tab Yielding, Rupture & Block Shear (AISC Sec. J4.2 & J4.3)
1. **Shear Yielding**: $R_{n,sy} = 0.60 F_y (d_p t_p) \quad (\phi = 1.00, \; \Omega = 1.50)$
2. **Shear Rupture**: $R_{n,sr} = 0.60 F_u [d_p - n(d_h + 1/16")] t_p \quad (\phi = 0.75, \; \Omega = 2.00)$
3. **Block Shear Rupture**:
   $$A_{gv} = [d_p - L_{ev}] t_p, \quad A_{nv} = A_{gv} - (n - 0.5)(d_h + 1/16") t_p, \quad A_{nt} = [L_{eh} - 0.5(d_h + 1/16")] t_p$$
   $$R_{n,bs} = 0.60 F_u A_{nv} + U_{bs} F_u A_{nt} \le 0.60 F_y A_{gv} + U_{bs} F_u A_{nt} \quad (U_{bs} = 1.0, \; \phi = 0.75, \; \Omega = 2.00)$$

### Step 5: Plate Flexure, Shear-Flexure Interaction & Buckling (*Extended Tabs*)
1. For extended shear tabs ($a > 3.5"$), compute moment $M = V \cdot a$ at the weld line or bolt line:
   - Gross flexural yielding: $M_n = F_y Z_p = F_y \frac{t_p d_p^2}{4} \quad (\phi = 0.90, \; \Omega = 1.67)$
   - Von Mises shear-flexure interaction:
     $$\left(\frac{V_u}{\phi V_{n,sy}}\right)^2 + \left(\frac{M_u}{\phi M_n}\right)^2 \le 1.00 \quad \text{(LRFD)} \qquad \text{or} \qquad \left(\frac{V_a}{V_{n,sy}/\Omega}\right)^2 + \left(\frac{M_a}{M_n/\Omega}\right)^2 \le 1.00 \quad \text{(ASD)}$$
   - Lateral-torsional buckling of extended plate per AISC Manual Part 9 ($F_{cr}$ based on $d_p / t_p$ and unbraced length $a$).

### Step 6: Support Weld & Supporting Member Web / HSS Wall Check (AISC Sec. J2.4, Ch. K & Manual Part 10)
1. **Double-Sided Fillet Weld**: Size $w \ge \frac{5}{8} t_p$ (`E70XX`) on both sides of the shear tab so the plate yields before the weld fractures (no eccentric weld moment check required for conventional tabs with $w \ge \frac{5}{8} t_p$; for extended tabs, verify weld under combined $V$ and $M = V \cdot a$ if support is rigid).
2. **Supporting W-Shape Web / Girder Web Check**: If framing into a thin column web or girder web, verify supporting web shear/flexural yielding per AISC Sec. J4.2.
3. **Supporting HSS Column Wall Checks (AISC Manual Part 10, *Single-Plate Connections to HSS* & AISC 360-22 Table K1.2)**:
   - **HSS Wall Slenderness Limit**: Verify that the HSS column wall is non-slender under axial compression per Table B4.1a ($b/t_{des} \le 1.40\sqrt{E/F_y} \approx 33.7$ for rectangular HSS; $D/t_{des} \le 0.11 E/F_y \approx 63.8$ for round HSS with $F_y = 50\text{ ksi}$). If slender, use a **through-plate connection** instead of a single-plate shear tab.
   - **HSS Wall Punching Shear Rupture**: Verify the HSS wall of design thickness $t_{des}$ ($0.93 t_{nom}$ for ERW ASTM A500; $1.00 t_{nom}$ for A1085) and tensile strength $F_{u,HSS}$ under eccentric shear $V_r$ at eccentricity $e$ (distance from HSS face to centroid of bolt group) per AISC Manual Part 10 ($\phi = 0.75, \; \Omega = 2.00$):
     $$V_u \cdot e \le \phi \frac{F_{u,HSS} \cdot t_{des} \cdot d_p^2}{5} \quad \text{(LRFD)} \qquad \text{or} \qquad V_a \cdot e \le \frac{F_{u,HSS} \cdot t_{des} \cdot d_p^2}{5 \cdot \Omega} \quad \text{(ASD)}$$
   - **Axial Force on Shear Tab (If Present)**: If the shear tab also transfers significant axial tension or compression into the HSS face, additionally check longitudinal plate-to-HSS wall plastification per AISC 360-22 Table K1.2.

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State | Demand | LRFD Capacity ($\phi R_n$) | ASD Capacity ($R_n / \Omega$) | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Plate Ductility ($t_{p,max}$)** | $t_p$ | $t_p \le d_b/2 + 1/16"$ (Conv.) | $t_p \le d_b/2 + 1/16"$ (Conv.) | AISC Manual Part 10 |
| **Eccentric Bolt Shear** | $V$ | $0.75 C F_{nv} A_b$ | $0.50 C F_{nv} A_b$ | AISC Sec. J3.6 & Part 7 |
| **Bolt Bearing / Tearout** | $V$ | $0.75 (C/n) \sum \min(r_v, r_{p,i}, r_{w,i})$ | $0.50 (C/n) \sum \min(r_v, r_{p,i}, r_{w,i})$ | AISC Sec. J3.10 |
| **Plate Shear Yield / Rupture** | $V$ | $1.00 (0.60 F_y A_{gv})$ / $0.75 (0.60 F_u A_{nv})$ | $0.667 (0.60 F_y A_{gv})$ / $0.50 (0.60 F_u A_{nv})$ | AISC Sec. J4.2 |
| **Block Shear Rupture** | $V$ | $0.75 R_{n,bs}$ | $0.50 R_{n,bs}$ | AISC Sec. J4.3 |
| **Shear-Flexure Interaction** | $V, M$ | $(V_u/\phi V_n)^2 + (M_u/\phi M_n)^2 \le 1.0$ | $(V_a/V_{a,allow})^2 + (M_a/M_{a,allow})^2 \le 1.0$ | AISC Manual Part 10 (Ext.) |
| **Double-Sided Fillet Weld** | $w$ | $w \ge \frac{5}{8} t_p$ (`E70XX`) | $w \ge \frac{5}{8} t_p$ (`E70XX`) | AISC Manual Part 10 |
| **HSS Wall Punching Shear** | $V \cdot e$ | $0.75 (F_{u,HSS} t_{des} d_p^2 / 5)$ | $0.50 (F_{u,HSS} t_{des} d_p^2 / 5)$ | AISC Manual Part 10 (HSS) |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Exceeding $t_{p,max}$ Causes Brittle Bolt Fracture**: Never arbitrarily thicken a conventional shear tab beyond $d_b/2 + 1/16"$ without checking $t_{p,max} = 6 M_{max} / (F_y d_p^2)$.
2. **Minimum Horizontal Edge Distance ($L_{eh} \ge 2.0 d_b$)**: Conventional Table 10-9 requires $L_{eh} \ge 2.0 d_b$ on **both** the shear tab and the beam web (beam end setback $c_{setback}$ must be subtracted when checking beam web $L_{eh}$!).
3. **No Top/Bottom Weld Returns**: Do not wrap fillet welds around the top and bottom edges of a shear tab if it restrains end rotation.
4. **Through-Plate for Slender HSS Columns**: Never weld a single-plate shear tab directly to a slender HSS column face ($b/t_{des} > 1.40\sqrt{E/F_y}$); detail a through-plate slotted through both HSS walls.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Design a conventional single-plate shear connection (shear tab) for a **`W18x35` ASTM A992 beam** ($d = 17.7", t_w = 0.300", T = 15.2", F_y = 50\text{ ksi}, F_u = 65\text{ ksi}$) framing into a `W14x90` column flange:
- **Applied Shear**: $V_u = 45.0\text{ kips}$ (LRFD), $V_a = 30.0\text{ kips}$ (ASD).
- **Trial Shear Tab**: `3/8" x 9"` ASTM A36 plate ($F_y = 36\text{ ksi}, F_u = 58\text{ ksi}$), weld-to-bolt distance $a = 3.0\text{ in.}$, **(3) `3/4"` dia. A325-N** bolts at $s = 3.0"$ pitch, $L_{ev} = 1.5"$, $L_{eh} = 1.5"$ ($= 2.0 d_b$).

### 7.2 Step-by-Step Solution
1. **Conventional Limits & Ductility Check**:
   - $a = 3.0" \le 3.5"$, $L_{eh} = 1.5" \ge 2.0(0.75") = 1.5"$, $d_p = 9.0" \ge 0.50(15.2") = 7.6" \implies \textbf{OK}$.
   - Ductility limit: $t_{p,max} = 0.75/2 + 1/16 = 7/16" = 0.4375" \ge t_p = 0.375" \implies \textbf{OK}$.
2. **Eccentric Bolt Shear (`AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv`)**:
   - Design eccentricity: $e = a / 2 = 3.0 / 2 = 1.50\text{ in.}$
   - From `Part7_Eccentric_Bolt_C_Coefficients.csv` for $n = 3, e_x = 1.5"$: $C = 2.59$.
   - Single bolt shear ($A_b = 0.4418\text{ in.}^2, F_{nv} = 54\text{ ksi}$): $r_v = 54 \times 0.4418 = 23.86\text{ kips/bolt}$.
   - **LRFD**: $\phi R_{n,bolts} = 0.75 \times 2.59 \times 23.86 = 46.34\text{ kips} \ge 45.0\text{ kips} \quad (D/C = 0.971) \implies \textbf{OK}$.
   - **ASD**: $R_{n,bolts}/\Omega = (2.59 \times 23.86) / 2.00 = 30.90\text{ kips} \ge 30.0\text{ kips} \quad (D/C = 0.971) \implies \textbf{OK}$.
3. **Bolt Bearing / Tearout on `W18x35` Web ($t_w = 0.300", F_u = 65\text{ ksi}$) & `3/8"` Plate**:
   - Web edge bolt ($l_c = 1.5 - 0.8125/2 = 1.094"$): $r_{n,web} = \min(1.2(1.094)(0.300)(65), 2.4(0.75)(0.300)(65)) = \min(25.60, 35.10) = 25.60 > r_v = 23.86\text{ kips}$. Bolt shear governs!
4. **Plate Shear Yielding, Rupture & Block Shear**:
   - Shear Yielding: $\phi R_{n,sy} = 1.00 \times 0.60 \times 36 \times (9.0 \times 0.375) = 72.90\text{ kips} \implies \textbf{OK}$.
   - Shear Rupture: $A_{nv} = [9.0 - 3(0.875)] \times 0.375 = 2.391\text{ in.}^2 \implies \phi R_{n,sr} = 0.75 \times 0.60 \times 58 \times 2.391 = 62.40\text{ kips} \implies \textbf{OK}$.
   - Block Shear: $A_{gv} = 7.5(0.375) = 2.813$, $A_{nv} = [7.5 - 2.5(0.875)](0.375) = 1.992$, $A_{nt} = [1.5 - 0.5(0.875)](0.375) = 0.398$:
     $$R_{n,bs} = 0.60(58)(1.992) + 1.0(58)(0.398) = 92.41\text{ kips} \le 0.60(36)(2.813) + 58(0.398) = 83.84\text{ kips}$$
     $$\phi R_{n,bs} = 0.75 \times 83.84 = 62.88\text{ kips} \ge 45.0\text{ kips} \implies \textbf{OK}$$
5. **Double-Sided Fillet Weld**: $w_{req} = \frac{5}{8} t_p = 0.234" \implies$ **Use `1/4"` E70XX fillet welds on both sides**.
