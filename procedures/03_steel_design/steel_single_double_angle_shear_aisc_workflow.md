# Single-Angle & Double-Angle Shear Connection Design Procedure (AISC 360-22 / Manual Part 10)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Chapter J (Sec. J2, J3, J4) & Chapter F/G (Coped Beam Checks).
  - **AISC Steel Construction Manual, 16th Edition**: Part 10 (Double-Angle Connections Tables 10-1 to 10-3; Single-Angle Connections Tables 10-10 to 10-11), Part 9 (Coped Beam Web Flexure & Local Buckling).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC_Manual_16th_Part10_Shear_Tab_and_Single_Angle_Design.csv`
  - `database/aisc_360/ch_j_connections/AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J3.2_Bolt_Strength.csv`

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $V_u, V_a$ | Factored (LRFD) or Allowable (ASD) beam end shear reaction | $\text{kips}$ | Structural Analysis |
| $L_a \times t_a, L_{angle}$ | Angle size (e.g. `L4x3-1/2x3/8`), thickness $t_a$, and length $L_{angle}$ | $\text{in.}$ | AISC Shapes Database |
| $g, t_w$ | Gauge on support leg ($g$) and supported beam web thickness ($t_w$) | $\text{in.}$ | Framing Geometry |
| $c, d_c, h_0$ | Cope length ($c$), cope depth ($d_c$), and remaining web depth ($h_0 = d - d_c$) | $\text{in.}$ | Coped Beam Geometry |

---

## 3. Eccentricity & Load Path Mechanics (Single vs. Double Angle)
1. **Double-Angle Connection (`2L`)**:
   - **Beam-Side Bolts**: In **double shear** ($n_s = 2$); eccentricity $e_{beam}$ is neglected per AISC Manual Part 10 (concentric shear). Note that bolt bearing on the **single beam web** ($t_w$) frequently governs!
   - **Support-Side Bolts**: In single shear ($n_s = 1$) across two outstanding legs; concentric ($e_{sup} = 0$).
2. **Single-Angle Connection (`1L`)**:
   - **Support-Side Bolts (Critical Eccentricity)**: Reaction acts at the centerline of the beam web, which is offset from the support-leg bolt line by $e_{sup} = g + \frac{t_w}{2}$. Use `AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv` to find $C$.
   - **Beam-Side Bolts**: Single shear ($n_s = 1$); eccentricity $e_{beam}$ is distance from support face to bolt line (neglected if $\le 3\text{ in.}$ per Part 10, or included via $C$).

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Detailing & Ductility Checks
- Angle thickness $t_a \le 5/8\text{ in.}$ (typically $1/4"$ to $3/8"$) to permit simple-connection end rotation.
- Verify entering/tightening clearances (AISC Manual Table 7-15) and bolt spacing ($s \ge 2\frac{2}{3} d_b$) and edge distances (Table J3.4).

### Step 2: Beam-Side & Support-Side Bolt Shear & Bearing (Sec. J3.6 & J3.10)
1. **Beam-Side**:
   - Double angle: $R_{n,v} = n \cdot (2 F_{nv} A_b)$; check bearing/tearout on single beam web ($t_w$) vs. two angles ($2 t_a$).
   - Single angle: $R_{n,v} = C \cdot F_{nv} A_b$ (with $e_{beam}$ if $> 3"$); check bearing/tearout on beam web ($t_w$) and single angle ($t_a$).
2. **Support-Side**:
   - Double angle: $R_{n,v} = n_{sup} \cdot F_{nv} A_b$; check bearing/tearout on angle legs ($t_a$) and supporting column/girder web.
   - Single angle: Compute $e_{sup} = g + t_w / 2$, look up $C$, and check $R_{n,v} = C \cdot F_{nv} A_b$.

### Step 3: Angle Shear Yielding, Rupture & Block Shear (Sec. J4.2 & J4.3)
- Check gross shear yielding ($0.60 F_y L_{angle} t_a$), net shear rupture ($0.60 F_u A_{nv}$), and block shear ($R_{n,bs}$, Eq. J4-5) on the angle leg(s).

### Step 4: Coped Beam Web Checks (AISC Manual Part 9) — *If Beam Is Coped*
1. **Coped Web Block Shear (Sec. J4.3)**: Check L-shaped block shear tearout at the coped beam end ($U_{bs} = 1.0$ for 1 vertical bolt row; $U_{bs} = 0.5$ for 2 vertical bolt rows).
2. **Coped Web Flexural Local Buckling (Manual Part 9, Eq. 9-6 to 9-12)**:
   - Applied moment at face of cope: $M_{cope} = V \cdot e_{cope}$ (where $e_{cope} = c + \text{setback}$).
   - For single-coped beam ($c \le 2d, d_c \le d/2$):
     $$F_{cr} = \frac{0.62 \pi E t_w^2}{c \cdot h_0} \cdot f \cdot k_1 \le F_y$$
     Where $f = 2(c/d)$ for $c/d \le 1.0$ (or $1 + c/d$ for $c/d > 1.0$), and $k_1 = 2.2(h_0/c)^{1.65}$ for $c/h_0 \le 1.0$ (or $2.2(h_0/c)$ for $c/h_0 > 1.0$).
   - Check $M_{cope} \le \phi_b F_{cr} S_{net}$ (LRFD, $\phi_b = 0.90$) or $F_{cr} S_{net} / 1.67$ (ASD).

---

## 5. Limit States Summary Table

| Limit State | Demand | LRFD Capacity ($\phi R_n$) | ASD Capacity ($R_n / \Omega$) | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Beam-Side Bolt Shear** | $V$ | $0.75 n_s n F_{nv} A_b$ (`2L`) / $0.75 C F_{nv} A_b$ (`1L`) | $0.50 R_n$ | AISC Sec. J3.6 & Part 10 |
| **Support-Side Bolt Shear** | $V$ | $0.75 n_{sup} F_{nv} A_b$ (`2L`) / $0.75 C F_{nv} A_b$ (`1L`) | $0.50 R_n$ | AISC Sec. J3.6 & Part 7 |
| **Web / Angle Bearing & Tearout** | $V$ | $0.75 \sum \min(1.2 l_c t F_u, 2.4 d_b t F_u)$ | $0.50 R_n$ | AISC Sec. J3.10 |
| **Angle Shear & Block Shear** | $V$ | $1.00 (0.60 F_y A_{gv})$ / $0.75 R_{n,bs}$ | $0.667 (0.60 F_y A_{gv})$ / $0.50 R_{n,bs}$ | AISC Sec. J4.2 & J4.3 |
| **Coped Beam Flexural Buckling** | $V \cdot e_{cope}$ | $0.90 F_{cr} S_{net}$ | $0.60 F_{cr} S_{net}$ | AISC Manual Part 9 |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Single-Angle Support Eccentricity ($e = g + t_w/2$)**: Never treat support-side bolts in a single-angle connection as concentric; eccentricity cuts a 2-bolt support leg capacity by $\sim 35\%\text{–}40\%$.
2. **Double-Angle Bearing on Thin Beam Web**: Even though double-angle beam bolts have double shear ($n_s = 2$), the **single beam web** ($t_w$) often governs over bolt shear.
3. **Double-Coped Beams**: If both top and bottom flanges are coped, check lateral-torsional buckling of the rectangular coped web ($h_0 \times t_w$) per Manual Part 9 Eq. 9-13.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Check a **Single-Angle `L4x3x3/8` (A36)** connection (`5.5"` long) supporting a **top-coped `W12x14` (A992)** beam ($d = 11.9", t_w = 0.200", c = 4.0", d_c = 1.5", h_0 = 10.4"$) framing to a `W18x35` girder web ($t_{w,gir} = 0.300"$) with **(2) `3/4"` A325-N** bolts on each leg ($s = 3.0", L_{ev} = 1.25", g = 1.75"$ on support leg):
- **Applied Shear**: $V_u = 18.0\text{ kips}$ (LRFD), $V_a = 12.0\text{ kips}$ (ASD).
1. **Support-Side Bolts (2 bolts, $e_{sup} = g + t_w/2 = 1.75 + 0.200/2 = 1.85\text{ in.}$)**:
   - Interpolating `AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv` for $n=2$ between $e_x=1.5"$ ($C=1.41$) and $e_x=2.0"$ ($C=1.20$): $C \approx 1.26$.
   - $\phi R_{n,sup} = 0.75 \times 1.26 \times (54 \times 0.4418) = 22.55\text{ kips} \ge 18.0\text{ kips} \quad (D/C = 0.798) \implies \textbf{OK}$.
   - $R_{n,sup}/\Omega = 22.55 / 1.50 = 15.03\text{ kips} \ge 12.0\text{ kips} \implies \textbf{OK}$.
2. **Beam-Side Bearing on `W12x14` Web ($t_w = 0.200", F_u = 65\text{ ksi}$)**:
   - Edge bolt ($l_c = 1.25 - 0.8125/2 = 0.844"$): $\phi r_{n,edge} = 0.75 \times 1.2(0.844)(0.200)(65) = 9.87\text{ kips}$.
   - Interior bolt ($l_c = 3.0 - 0.8125 = 2.188"$): $\phi r_{n,int} = 0.75 \times 2.4(0.75)(0.200)(65) = 17.55\text{ kips}$.
   - Total beam-side bearing: $\phi R_{n,brg} = 9.87 + 17.55 = 27.42\text{ kips} \ge 18.0\text{ kips} \implies \textbf{OK}$.
3. **Coped Beam Flexure ($c = 4.0", h_0 = 10.4", S_{net} = 3.60\text{ in.}^3$)**:
   - $f = 2(4.0/11.9) = 0.672$, $k_1 = 2.2(10.4/4.0)^{1.65} = 10.64 \implies F_{cr} > F_y = 50\text{ ksi}$ (use $F_y = 50\text{ ksi}$).
   - $\phi M_n = 0.90 \times 50 \times 3.60 = 162.0\text{ kip-in.} \ge M_u = 18.0 \times 4.0 = 72.0\text{ kip-in.} \implies \textbf{OK}$.
