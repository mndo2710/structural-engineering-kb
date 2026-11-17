# HSS-to-HSS Moment & Shear Connection Design Procedure (AISC 360-22 Ch. K & Design Guide 24)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Chapter K (Section K3: HSS-to-HSS Truss/Axial Connections; Section K4: HSS-to-HSS Moment Connections), Chapter J (Welds & Concentrated Forces), and Section B4.2 ($t_{des} = 0.93 t_{nom}$ for ERW HSS).
  - **AISC Steel Design Guide No. 24 (2nd Edition, 2024)**: *Hollow Structural Section Connections*.
  - **AWS D1.1/D1.1M**: *Structural Welding Code—Steel*, Clause 10 (Tubular Structures).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_K3.2_K4.2_HSS_Connections.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.5_Welded_Joints.csv`

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $H, B, t, F_y, F_u$ | Chord (column) height, width, design wall thickness ($0.93 t_{nom}$), material | $\text{in.}, \text{ksi}$ | ASTM A500 Gr. C ($50/62$) or A1085 ($50/65$) |
| $H_b, B_b, t_b, F_{yb}$ | Branch (beam) height, width, design wall thickness, yield stress | $\text{in.}, \text{ksi}$ | AISC Shapes Database |
| $\beta, \eta$ | Width ratio $\beta = B_b / B$; aspect ratio $\eta = H_b / (B \sin\theta)$ | — | AISC Ch. K ($0.25 \le \beta \le 1.0$) |
| $P_r, V_r, M_{r\text{-}ip}, M_{r\text{-}op}$ | Required axial, shear, in-plane moment, and out-of-plane moment | $\text{kips}, \text{kip-in.}$ | Structural Analysis |
| $P_{ro}, M_{ro}$ | Existing axial compression & moment in chord on compression side | $\text{kips}, \text{kip-in.}$ | Chord Stress Interaction $Q_f$ |

---

## 3. Connection Classification & Limits of Applicability
- **Stepped Connections ($\beta = B_b / B < 1.0$)**: Branch is narrower than chord. Classified as **Partially Restrained (PR)** unless stiffened with collar/diaphragm plates. Governed by **chord face plastification** or **punching shear**.
- **Matched Connections ($\beta = B_b / B = 1.0$)**: Branch webs align flush with chord sidewalls. Classified as **Fully Restrained (FR)**. Governed by **chord sidewall yielding/crippling/buckling** and **branch uneven load distribution ($b_{eoi}$)**.
- **Ductility & Slenderness Limits (Table K4.2A)**: $B/t \le 35$, $H/t \le 35$, $F_y \le 52\text{ ksi}$, $F_y / F_u \le 0.80$ (both ASTM A500 Gr. C and A1085 satisfy).

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Chord Stress Interaction Factor ($Q_f$, AISC Sec. K3.3 & K4.3)
- If chord connecting face is in **tension**: $Q_f = 1.00$.
- If chord connecting face is in **compression**, compute utilization ratio $U = \left|\frac{P_{ro}}{F_y A_g} + \frac{M_{ro}}{F_y S}\right|$:
  $$Q_f = 1.30 - 0.40 \left(\frac{U}{\beta}\right) \le 1.00 \quad (\text{Rectangular HSS})$$

### Step 2: Rectangular HSS-to-HSS Moment Limit States (`AISC360-22_Table_K4.2`)
1. **For Stepped Connections ($\beta \le 0.85$) — Chord Wall Plastification**:
   - In-Plane: $M_{n\text{-}ip} = F_y t^2 H_b \left[\frac{1}{2\eta} + \frac{2}{\sqrt{1-\beta}} + \frac{\eta}{1-\beta}\right] Q_f \qquad (\phi = 1.00, \; \Omega = 1.50)$
   - Out-of-Plane: $M_{n\text{-}op} = F_y t^2 \left[\frac{0.5 H_b (1+\beta)}{1-\beta} + \sqrt{\frac{2 B B_b (1+\beta)}{1-\beta}}\right] Q_f \qquad (\phi = 1.00, \; \Omega = 1.50)$
2. **For Matched / Near-Matched Connections ($0.85 < \beta \le 1.0$)**:
   - **Local Yielding of Chord Sidewalls** ($\phi = 1.00, \; \Omega = 1.50$, $F_y^* = F_y$ for T-conn., $0.80 F_y$ for Cross-conn.):
     $$M_{n\text{-}ip} = 0.5 F_y^* t (H_b + 5t)^2, \qquad M_{n\text{-}op} = F_y^* t (B - t)(H_b + 5t)$$
   - **Uneven Load Distribution in Branch** ($\phi = 0.95, \; \Omega = 1.58$):
     $$b_{eoi} = \frac{10}{B/t} \left(\frac{F_y t}{F_{yb} t_b}\right) B_b \le B_b$$
     $$M_{n\text{-}ip} = F_{yb} \left[Z_b - \left(1 - \frac{b_{eoi}}{B_b}\right) B_b H_b t_b\right], \qquad M_{n\text{-}op} = F_{yb} \left[Z_b - 0.5\left(1 - \frac{b_{eoi}}{B_b}\right)^2 B_b^2 t_b\right]$$
   - **Chord Distortional Failure (Out-of-Plane Only)** ($\phi = 1.00, \; \Omega = 1.50$):
     $$M_{n\text{-}op} = 2 F_y t \left[H_b t + \sqrt{B H t (B + H)}\right]$$

### Step 3: Combined Axial, In-Plane & Out-of-Plane Moment Interaction (Sec. K4.3)
- Evaluate all axial limit states from `AISC360-22_Table_K3.2` ($P_c$) and moment limit states ($M_{c\text{-}ip}, M_{c\text{-}op}$):
  $$\frac{P_r}{P_c} + \left(\frac{M_{r\text{-}ip}}{M_{c\text{-}ip}}\right)^2 + \frac{M_{r\text{-}op}}{M_{c\text{-}op}} \le 1.00$$

### Step 4: Weld Design & Effective Weld Length (AISC Sec. K5 & J2.4)
- **No Directional Increase**: Do **not** apply $(1 + 0.5\sin^{1.5}\theta)$ to fillet welds at rectangular HSS ends (Sec. J2.4(b)(2)).
- **Matched Connections ($\beta = 1.0$)**: Branch vertical sidewalls align with the rounded corners of the chord, requiring **flare-bevel groove welds** ($E = \frac{5}{16} R = \frac{5}{8} t_{nom}$) along the corners unless backed.
- **Effective Weld Properties ($S_{w,eff}, Z_{w,eff}$)**: Account for uneven load distribution along transverse walls ($b_{eoi}$) per AISC Sec. K5 when sizing welds.

---

## 5. Limit States Summary Table

| Limit State | Applicability | $\phi$ (LRFD) | $\Omega$ (ASD) | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Chord Wall Plastification** | $\beta \le 0.85$ | $1.00$ | $1.50$ | AISC Table K3.2 / K4.2 |
| **Chord Face Punching Shear** | $0.85 < \beta \le 1 - 2t/B$ | $0.95$ | $1.58$ | AISC Table K3.2 |
| **Chord Sidewall Local Yielding** | $\beta = 1.0$ | $1.00$ | $1.50$ | AISC Table K3.2 / K4.2 |
| **Branch Uneven Load ($b_{eoi}$)** | $0.85 \le \beta \le 1.0$ | $0.95$ | $1.58$ | AISC Table K3.2 / K4.2 |
| **Combined Axial + Moment** | All HSS-to-HSS | — | — | AISC Sec. K4.3 ($\le 1.00$) |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Use $t_{des} = 0.93 t_{nom}$ for ERW HSS (AISC Sec. B4.2)**: For ASTM A500 Gr. C ERW HSS, always use $0.93 t_{nom}$ in all Chapter K formulas (whereas ASTM A1085 uses $1.00 t_{nom}$).
2. **Matched Width Flare-Bevel Groove Welds**: When $\beta = 1.0$, detail flare-bevel groove welds along the two longitudinal edges where the branch meets the chord corner radii.
3. **Shear Connection to HSS Column Face**: When connecting a W-beam to an HSS column via a shear tab, check **chord face plastification / punching shear** of the HSS wall under the eccentricity $e = a$ per AISC Manual Part 10 p. 10-95 & Table K1.2.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Check an orthogonal ($	heta = 90^\circ$) T-connection between an **`HSS8x6x1/4` branch beam** ($H_b = 8", B_b = 6", t_b = 0.233", Z_{xb} = 17.7\text{ in.}^3$) and an **`HSS8x8x3/8` chord column** ($H = 8", B = 8", t = 0.349", A_g = 10.4\text{ in.}^2$, ASTM A500 Gr. C, $F_y = 50\text{ ksi}$):
- **Applied In-Plane Moment**: $M_{u\text{-}ip} = 240\text{ kip-in.}$ (LRFD), $M_{a\text{-}ip} = 160\text{ kip-in.}$ (ASD). Chord compression $P_{uo} = 100\text{ kips}$ ($U = 100 / (50 \times 10.4) = 0.192$).
1. **Geometry & $Q_f$**: $\beta = 6 / 8 = 0.75 \le 0.85$; $\eta = 8 / 8 = 1.00$; $Q_f = 1.30 - 0.40(0.192 / 0.75) = 1.198 \implies 1.00$.
2. **Chord Wall Plastification (Table K4.2, $\beta = 0.75 \le 0.85$)**:
   $$M_{n\text{-}ip} = 50 \times (0.349)^2 \times 8.0 \times \left[\frac{1}{2(1.0)} + \frac{2}{\sqrt{1 - 0.75}} + \frac{1.0}{1 - 0.75}\right] \times 1.00$$
   $$M_{n\text{-}ip} = 48.72 \times [0.50 + 4.00 + 4.00] = 48.72 \times 8.50 = 414.1\text{ kip-in.}$$
   - **LRFD**: $\phi M_{n\text{-}ip} = 1.00 \times 414.1 = 414.1\text{ kip-in.} \ge 240\text{ kip-in.} \quad (D/C = 0.580) \implies \textbf{OK}$.
   - **ASD**: $M_{n\text{-}ip}/\Omega = 414.1 / 1.50 = 276.1\text{ kip-in.} \ge 160\text{ kip-in.} \quad (D/C = 0.580) \implies \textbf{OK}$.
