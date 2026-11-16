# Structural Steel Bolted Connection Design Procedure (ANSI/AISC 360-22 Section J3 & J4)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Chapter J (Section J3: Bolts and Threaded Parts; Section J4: Affected Elements of Members and Connecting Elements) & Chapter B (Section B4.3b: Net Area).
  - **AISC Steel Construction Manual, 16th Edition**: Part 7 (Design Considerations for Bolts), Part 9 (Connecting Elements & Prying Action), Part 10 (Simple Shear Connections).
  - **RCSC Specification (2020)**: *Specification for Structural Joints Using High-Strength Bolts* (Snug-Tightened, Pretensioned, and Slip-Critical Joint Requirements).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J3.2_Bolt_Strength.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J3.3_J3.4_J3.5_Bolt_Holes_and_Edge_Distances.csv`
- **Design Philosophies (Dual LRFD & ASD)**:
  - **LRFD**: $R_u \le \phi R_n$ (e.g., $\phi = 0.75$ for bolt shear, tension, bearing, tearout, net rupture, block shear; $\phi = 0.90$ for gross yielding; $\phi = 1.00$ for slip-critical standard holes).
  - **ASD**: $R_a \le R_n / \Omega$ (e.g., $\Omega = 2.00$ for bolt shear, tension, bearing, tearout, net rupture, block shear; $\Omega = 1.67$ for gross yielding; $\Omega = 1.50$ for slip-critical standard holes).

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $V_u, V_a$ | Factored (LRFD) or Allowable (ASD) applied shear force | $\text{kips}$ | ASCE 7-22 Load Combinations |
| $T_u, T_a$ | Factored (LRFD) or Allowable (ASD) applied axial tension force | $\text{kips}$ | ASCE 7-22 Load Combinations |
| $d$ | Nominal bolt diameter ($1/2"$, $5/8"$, $3/4"$, $7/8"$, $1"$, etc.) | $\text{in.}$ | `AISC360-22_Table_J3.3_...csv` |
| $\text{Group}, \text{Thread}$ | Bolt specification (`A307`, `Group A / F3125 A325`, `Group B / A490`) & threads (`N` vs. `X`) | — | `AISC360-22_Table_J3.2_Bolt_Strength.csv` |
| $n_b, n_s$ | Total number of bolts ($n_b$) and number of shear planes per bolt ($n_s = 1$ single, $2$ double) | — | Connection Geometry |
| $d_h$ | Nominal bolt hole diameter (`STD`, `OVS`, `SSL`, `LSL`) | $\text{in.}$ | `AISC360-22_Table_J3.3_...csv` |
| $s, l_e$ | Center-to-center bolt spacing ($s$) and edge distance ($l_e$) | $\text{in.}$ | `AISC360-22_Table_J3.4_J3.5` |
| $t, F_y, F_u$ | Connected plate thickness ($t$), yield stress ($F_y$), and tensile strength ($F_u$) | $\text{in.}, \text{ksi}$ | ASTM A36 ($36/58$), A572 Gr. 50 ($50/65$), A992 ($50/65$) |

---

## 3. Detailing Limits & Joint Classification

### 3.1 Bolt Hole Dimensions, Spacing, and Edge Distances (AISC Sec. J3.2–J3.5)
- **Nominal Hole Dimensions (Table J3.3)**: Standard hole $d_h = d + 1/16"$ for $d \le 7/8"$, and $d + 1/8"$ for $d \ge 1"$.
- **Minimum Spacing (Sec. J3.3)**:
  $$s_{min} = 2\frac{2}{3} d \quad (\text{Preferred: } s_{pref} = 3.0 d)$$
- **Minimum Edge Distance (Table J3.4 & J3.5)**:
  $$l_{e,min} = l_{e,Table\,J3.4} + C_2 \quad (C_2 = 0\text{ for Standard Holes})$$
- **Maximum Spacing & Edge Distance (Sec. J3.5)**:
  $$l_{e,max} = \min(12 t, \; 6\text{ in.}), \qquad s_{max} = \min(24 t, \; 12\text{ in.}) \text{ (painted/interior)}$$

### 3.2 Bearing-Type vs. Slip-Critical Joint Selection (RCSC Sec. 4 & AISC Sec. J3.1)
- **Bearing-Type (Snug-Tightened or Pretensioned)**: Standard economical choice for static gravity/wind shear connections using standard holes (or short slots perpendicular to load).
- **Slip-Critical (SC) Mandatory Cases**: Joints subject to fatigue with load reversal, joints using oversized holes (`OVS`), joints using slotted holes parallel to load, and joints where slip at faying surfaces would cause excessive drift or loss of stability.

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Bolt Shear Strength (AISC Sec. J3.6, Eq. J3-1)
1. Compute nominal bolt area $A_b = \frac{\pi d^2}{4}$ ($\text{in.}^2$).
2. Look up $F_{nv}$ ($\text{ksi}$) from `AISC360-22_Table_J3.2_Bolt_Strength.csv` (`54 ksi` for Group A-N; `68 ksi` for Group A-X and Group B-N; `84 ksi` for Group B-X). If connection length $> 38\text{ in.}$, reduce $F_{nv}$ by $0.833$.
3. Nominal shear capacity of $n_b$ bolts with $n_s$ shear planes:
   $$R_{n,v} = F_{nv} \cdot A_b \cdot n_s \cdot n_b \quad (\text{kips})$$
   - **LRFD**: $\phi R_{n,v} = 0.75 \cdot R_{n,v}$
   - **ASD**: $R_{n,v} / \Omega = R_{n,v} / 2.00$

### Step 2: Bolt Tension & Combined Tension-Shear Interaction (AISC Sec. J3.6 & J3.7)
1. **Pure Tension (Eq. J3-1)**: Look up $F_{nt}$ ($\text{ksi}$) (`90 ksi` Group A; `113 ksi` Group B):
   $$R_{n,t} = F_{nt} \cdot A_b \cdot n_b \quad (\text{kips}), \qquad \phi = 0.75, \; \Omega = 2.00$$
2. **Combined Tension and Shear in Bearing-Type Connections (Sec. J3.7, Eq. J3-2 & J3-3a/b)**:
   - Required shear stress per bolt: $f_{rv} = \frac{V}{A_b \cdot n_s \cdot n_b}$ ($\text{ksi}$).
   - Modified nominal tensile stress $F'_{nt} \le F_{nt}$:
     - **LRFD**: $F'_{nt} = 1.3 F_{nt} - \left(\frac{F_{nt}}{0.75 F_{nv}}\right) f_{rv} \le F_{nt}$
     - **ASD**: $F'_{nt} = 1.3 F_{nt} - \left(\frac{2.00 F_{nt}}{F_{nv}}\right) f_{rv} \le F_{nt}$
   - Check $T_u \le 0.75 F'_{nt} A_b n_b$ (LRFD) or $T_a \le (F'_{nt} A_b n_b) / 2.00$ (ASD).
   *(Note: If $f_{rv} \le 0.30 \phi F_{nv}$ [LRFD] or $0.30 (F_{nv}/\Omega)$ [ASD], and $f_{rt} \le 0.30 \phi F_{nt}$, combined interaction need not be checked).*

### Step 3: Slip-Critical Resistance (AISC Sec. J3.8, Eq. J3-4) — *When Required*
1. Look up minimum bolt pretension $T_b$ ($\text{kips}$) from Table J3.1 (`AISC360-22_Table_J3.2_Bolt_Strength.csv`), mean slip coefficient $\mu$ ($0.30$ Class A, $0.50$ Class B), $D_u = 1.13$, and filler factor $h_f$ ($1.00$ for no/one filler, $0.85$ for $\ge 2$ fillers):
   $$R_{n,slip} = \mu \cdot D_u \cdot h_f \cdot T_b \cdot n_s \cdot n_b \quad (\text{kips})$$
   - **Standard & Short-Slot Perp. Holes**: $\phi = 1.00$ (LRFD), $\Omega = 1.50$ (ASD).
   - **Oversized & Short-Slot Parallel Holes**: $\phi = 0.85$ (LRFD), $\Omega = 1.76$ (ASD).
   - **Long-Slot Holes**: $\phi = 0.70$ (LRFD), $\Omega = 2.14$ (ASD).
2. If simultaneous tension $T$ is present, multiply slip capacity by $k_{sc} = 1 - \frac{T_u}{D_u T_b n_b}$ (LRFD) or $1 - \frac{1.5 T_a}{D_u T_b n_b}$ (ASD).

### Step 4: Bolt Bearing and Tearout at Bolt Holes (AISC Sec. J3.10, Eq. J3-6)
Check **each connected ply** separately using its thickness $t$ and tensile strength $F_u$:
1. **Clear Distances ($l_c$)**:
   - Edge bolt clear distance to free edge: $l_{c,edge} = l_e - \frac{d_h}{2}$
   - Interior bolt clear distance between holes: $l_{c,int} = s - d_h$
   *(Note: Use actual hole dimension $d_h$ parallel to force).*
2. **Bearing & Tearout Capacity per Bolt** ($\phi = 0.75$, $\Omega = 2.00$):
   - **When deformation at service load IS a design consideration** (Standard case, Eq. J3-6a):
     $$R_{n,i} = \min\left(1.2 \cdot l_{c,i} \cdot t \cdot F_u,\;\; 2.4 \cdot d \cdot t \cdot F_u\right)$$
   - **When deformation at service load is NOT a design consideration** (Eq. J3-6b):
     $$R_{n,i} = \min\left(1.5 \cdot l_{c,i} \cdot t \cdot F_u,\;\; 3.0 \cdot d \cdot t \cdot F_u\right)$$
   - **Long-Slotted Holes Perpendicular to Load** (Eq. J3-6c):
     $$R_{n,i} = \min\left(1.0 \cdot l_{c,i} \cdot t \cdot F_u,\;\; 2.0 \cdot d \cdot t \cdot F_u\right)$$
3. Sum over all bolts in the group: $R_{n,brg} = \sum_{i=1}^{n_b} R_{n,i}$ (and verify $R_n \le R_{n,bolt\,shear}$ per bolt).

### Step 5: Connecting Element Strength (AISC Sec. J4)
1. **Tensile Yielding (Sec. J4.1a, Eq. J4-1)**:
   $$R_n = F_y \cdot A_g \qquad (\phi = 0.90, \; \Omega = 1.67)$$
2. **Tensile Rupture (Sec. J4.1b, Eq. J4-2)**:
   - Effective hole width for net area per Sec. B4.3b: $d_{h,eff} = d_h + 1/16\text{ in.}$
   $$A_n = A_g - \sum (d_{h,eff} \cdot t), \qquad A_e = U \cdot A_n, \qquad R_n = F_u \cdot A_e \qquad (\phi = 0.75, \; \Omega = 2.00)$$
3. **Shear Yielding & Shear Rupture (Sec. J4.2, Eq. J4-3 & J4-4)**:
   - **Shear Yielding**: $R_n = 0.60 \cdot F_y \cdot A_{gv} \qquad (\phi = 1.00, \; \Omega = 1.50)$
   - **Shear Rupture**: $R_n = 0.60 \cdot F_u \cdot A_{nv} \qquad (\phi = 0.75, \; \Omega = 2.00)$
4. **Block Shear Rupture (Sec. J4.3, Eq. J4-5)**:
   $$R_n = 0.60 \cdot F_u \cdot A_{nv} + U_{bs} \cdot F_u \cdot A_{nt} \le 0.60 \cdot F_y \cdot A_{gv} + U_{bs} \cdot F_u \cdot A_{nt} \qquad (\phi = 0.75, \; \Omega = 2.00)$$
   Where $U_{bs} = 1.0$ for uniform tension stress (most gusset plates, angles, single-row shear tabs), or $U_{bs} = 0.5$ for non-uniform tension stress (coped beams with multiple bolt rows).

### Step 6: Prying Action for Bolts in Tension (AISC Manual Part 9) — *When Connected via Flange/Angle/Tee*
1. When tension is applied through a flexible plate/angle leg with gauge $b$ from bolt centerline to stem/weld face and edge distance $a \le 1.25b$, check prying force $q$ per AISC Manual 16th Ed. Part 9 ($p$ = tributary length per bolt, $\delta = 1 - d'/p$, $\rho = b'/a'$):
   - Required flange thickness to eliminate prying ($\alpha' = 0$):
     $$t_{min} = \sqrt{\frac{4.0 \cdot T_u \cdot b'}{\phi \cdot p \cdot F_u}} \quad (\text{LRFD}) \quad \text{or} \quad \sqrt{\frac{4.0 \cdot \Omega \cdot T_a \cdot b'}{p \cdot F_u}} \quad (\text{ASD})$$

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State | Demand | LRFD Design Capacity ($\phi R_n$) | ASD Allowable Capacity ($R_n / \Omega$) | Code Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Bolt Shear** | $V$ | $0.75 F_{nv} A_b n_s n_b$ | $0.50 F_{nv} A_b n_s n_b$ | AISC Sec. J3.6, Eq. J3-1 |
| **Bolt Tension** | $T$ | $0.75 F_{nt} A_b n_b$ | $0.50 F_{nt} A_b n_b$ | AISC Sec. J3.6, Eq. J3-1 |
| **Combined Shear & Tension** | $T$ | $0.75 F'_{nt} A_b n_b$ | $0.50 F'_{nt} A_b n_b$ | AISC Sec. J3.7, Eq. J3-2 |
| **Slip-Critical (STD Holes)** | $V$ | $1.00 \mu D_u h_f T_b n_s n_b$ | $0.667 \mu D_u h_f T_b n_s n_b$ | AISC Sec. J3.8, Eq. J3-4 |
| **Bolt Bearing / Tearout** | $V$ | $0.75 \sum \min(1.2 l_c t F_u, 2.4 d t F_u)$ | $0.50 \sum \min(1.2 l_c t F_u, 2.4 d t F_u)$ | AISC Sec. J3.10, Eq. J3-6a |
| **Plate Tensile Yield / Rupture** | $T$ | $0.90 F_y A_g$ / $0.75 F_u A_e$ | $0.60 F_y A_g$ / $0.50 F_u A_e$ | AISC Sec. J4.1 |
| **Plate Shear Yield / Rupture** | $V$ | $1.00 (0.60 F_y A_{gv})$ / $0.75 (0.60 F_u A_{nv})$ | $0.667 (0.60 F_y A_{gv})$ / $0.50 (0.60 F_u A_{nv})$ | AISC Sec. J4.2 |
| **Block Shear Rupture** | $V$ or $T$ | $0.75 R_n$ (Eq. J4-5) | $0.50 R_n$ (Eq. J4-5) | AISC Sec. J4.3 |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Mixing Up $d_h$ (Tearout) vs. $d_h + 1/16"$ (Net Tension/Shear Area)**:
   - For **bolt tearout** ($l_c = s - d_h$ or $l_e - d_h/2$), use the **actual nominal hole dimension $d_h$** from Table J3.3 ($13/16"$ for $3/4"$ bolt). For **net section tension/shear rupture** ($A_n, A_{nv}, A_{nt}$), AISC Sec. B4.3b requires adding **$1/16\text{ in.}$** to $d_h$ ($14/16" = 7/8"$ for $3/4"$ bolt).
2. **Thread Condition Default (`N` vs. `X`)**:
   - Always design bolts as **Threads Included (`N`)** unless the connection geometry is explicitly verified to exclude threads from every shear plane and noted on the drawings (`A325-X` or `Group A-X`).
3. **Oversized Holes Prohibited in Bearing-Type Shear Connections**:
   - Per AISC Sec. J3.2, **oversized holes (`OVS`) are ONLY permitted in slip-critical connections** (never in bearing-type shear connections).
4. **Block Shear $U_{bs} = 0.5$ vs. $1.0$**:
   - For a coped beam web with **two vertical lines** of bolts, tension stress on the horizontal plane is non-uniform ($U_{bs} = 0.5$); for a single vertical line of bolts, $U_{bs} = 1.0$.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
Check a single-plate bolted lap splice transferring axial tension between a **`3/8" x 6"` ASTM A36 plate** ($F_y = 36\text{ ksi}, F_u = 58\text{ ksi}$) and a thicker gusset plate (`1/2"` A36) using **(4) `3/4"` dia. Group A (F3125 Gr. A325-N)** bolts in **2 rows x 2 columns** with standard holes ($d_h = 13/16"$):
- **Bolt Layout**: Longitudinal spacing $s = 3.0\text{ in.}$, End distance $l_e = 1.5\text{ in.}$, Gauge $g = 3.0\text{ in.}$ ($1.5"$ to side edges).
- **Applied Axial Tension**: $T_u = 68.0\text{ kips}$ (LRFD), $T_a = 45.0\text{ kips}$ (ASD).

### 7.2 Step-by-Step Solution

#### 1. Detailing Checks (`AISC360-22_Table_J3.3_J3.4_J3.5`)
- Standard hole: $d_h = 13/16" = 0.8125\text{ in.}$
- Min spacing: $s = 3.0" \ge 2\frac{2}{3}(0.75") = 2.00" \implies \textbf{OK}$ (also $\ge 3d = 2.25"$).
- Min edge distance: $l_e = 1.50" \ge 1.00" \text{ (Table J3.4)} \implies \textbf{OK}$.
- Max edge distance: $l_e = 1.50" \le \min(12 \times 0.375", 6") = 4.50" \implies \textbf{OK}$.

#### 2. Bolt Shear Strength (Sec. J3.6)
- $A_b = \frac{\pi (0.75)^2}{4} = 0.4418\text{ in.}^2$, $F_{nv} = 54\text{ ksi}$ (Group A-N), $n_s = 1$, $n_b = 4$:
  $$R_{n,v} = 54 \times 0.4418 \times 1 \times 4 = 95.43\text{ kips}$$
  - **LRFD**: $\phi R_{n,v} = 0.75 \times 95.43 = 71.57\text{ kips} \ge 68.0\text{ kips} \quad (D/C = 0.950) \implies \textbf{OK}$
  - **ASD**: $R_{n,v}/\Omega = 95.43 / 2.00 = 47.71\text{ kips} \ge 45.0\text{ kips} \quad (D/C = 0.943) \implies \textbf{OK}$

#### 3. Bolt Bearing and Tearout on `3/8"` Plate (Sec. J3.10, Deformation Considered)
- Edge bolts (2 bolts): $l_{c,edge} = 1.50 - 0.8125/2 = 1.0938\text{ in.}$
  $$R_{n,edge} = \min(1.2 \times 1.0938 \times 0.375 \times 58,\; 2.4 \times 0.75 \times 0.375 \times 58) = \min(28.55,\; 39.15) = 28.55\text{ kips/bolt}$$
- Interior bolts (2 bolts): $l_{c,int} = 3.00 - 0.8125 = 2.1875\text{ in.}$
  $$R_{n,int} = \min(1.2 \times 2.1875 \times 0.375 \times 58,\; 39.15) = \min(57.09,\; 39.15) = 39.15\text{ kips/bolt}$$
- Note: Bolt shear per bolt $= 95.43 / 4 = 23.86\text{ kips/bolt}$ governs over both $28.55$ and $39.15\text{ kips/bolt}$!
  $$\phi R_{n,brg} = 0.75 \times (2 \times 28.55 + 2 \times 39.15) = 101.55\text{ kips} \ge 68.0\text{ kips} \implies \textbf{OK}$$

#### 4. `3/8" x 6"` Plate Tensile Yielding & Net Rupture (Sec. J4.1)
- **Gross Yielding**: $A_g = 0.375 \times 6.0 = 2.25\text{ in.}^2$, $R_n = 36 \times 2.25 = 81.00\text{ kips}$
  - **LRFD**: $\phi R_n = 0.90 \times 81.00 = 72.90\text{ kips} \ge 68.0\text{ kips} \quad (D/C = 0.933) \implies \textbf{OK}$
  - **ASD**: $R_n / \Omega = 81.00 / 1.67 = 48.50\text{ kips} \ge 45.0\text{ kips} \quad (D/C = 0.928) \implies \textbf{OK}$
- **Net Rupture**: Effective hole width $= d_h + 1/16" = 7/8" = 0.875\text{ in.}$
  $$A_n = 2.25 - 2 \times 0.875 \times 0.375 = 1.594\text{ in.}^2, \quad U = 1.0 \implies R_n = 58 \times 1.594 = 92.44\text{ kips}$$
  - **LRFD**: $\phi R_n = 0.75 \times 92.44 = 69.33\text{ kips} \ge 68.0\text{ kips} \quad (D/C = 0.981) \implies \textbf{OK}$
  - **ASD**: $R_n / \Omega = 92.44 / 2.00 = 46.22\text{ kips} \ge 45.0\text{ kips} \quad (D/C = 0.974) \implies \textbf{OK}$
