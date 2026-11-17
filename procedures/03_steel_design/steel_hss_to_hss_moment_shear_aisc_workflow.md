# HSS-to-HSS Beam-to-Column Welded Moment & Shear Connection Design Procedure (AISC 360-22 Ch. K, Ch. J & Design Guide 24)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 22.
  - **ASCE/SEI 7-22**: *Minimum Design Loads and Associated Criteria for Buildings and Other Structures*, Section 2.3 (LRFD) and Section 2.4 (ASD).
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings*, Section B4.2 ($t_{des} = 0.93 t_{nom}$ for ERW HSS), Chapters D–G, Chapter H (Sec. H1.1 & Sec. H3 Torsion Interaction), Chapter J (Sec. J2 Welds, Sec. J4 Affected Elements, Sec. J10 Concentrated Forces), and Chapter K (Sec. K1, K3, K4, K5 HSS Connections).
  - **AISC Steel Design Guide No. 24 (2nd Edition, 2024)**: *Hollow Structural Section Connections* (Chapters 2, 3, 6, 10).
  - **AWS D1.1/D1.1M**: *Structural Welding Code—Steel*, Clause 10 (Tubular Structures).
- **Referenced Repository Databases**:
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_K3.2_K4.2_HSS_Connections.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.4.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.5_Welded_Joints.csv`

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $H, B, t, F_y, F_u$ | Chord (column) height, width, design wall thickness ($0.93 t_{nom}$ A500; $1.00 t_{nom}$ A1085), material | $\text{in.}, \text{ksi}$ | ASTM A500 Gr. C ($50/62$) or A1085 ($50/65$) |
| $H_b, B_b, t_b, F_{yb}, F_{ub}$ | Branch (beam) height, width, design wall thickness, material | $\text{in.}, \text{ksi}$ | AISC 16th Ed. Shapes Database |
| $\theta$ | Acute angle between branch longitudinal axis and chord longitudinal axis ($30^\circ \le \theta \le 90^\circ$) | $\text{deg}$ | Framing Geometry ($l_b = H_b / \sin\theta$) |
| $\beta, \eta, \gamma$ | Width ratio $\beta = B_b / B$; aspect ratio $\eta = H_b / (B \sin\theta)$; slenderness $\gamma = B / (2t)$ | — | AISC Ch. K ($0.25 \le \beta \le 1.0$) |
| $P_r, V_{ry}, V_{rz}, M_{r\text{-}ip}, M_{r\text{-}op}, T_r$ | Required branch axial, in-plane/out-of-plane shear, in-plane/out-of-plane moment, and torsion | $\text{kips}, \text{kip-in.}$ | ASCE 7-22 Load Combinations (LRFD/ASD) |
| $P_{ro}, M_{ro}$ | Existing axial compression & moment in chord on highest-stressed compression side | $\text{kips}, \text{kip-in.}$ | Chord Stress Interaction $Q_f$ |

---

## 3. Connection Classification, Force Resolution & Limits of Applicability
- **Stepped Connections ($\beta \le 0.85$)**: Branch webs land on the flexible flat connecting face of the HSS column. Classified as **Partially Restrained (PR)** per AISC Sec. B3.4b(b) unless stiffened with collar/diaphragm plates. Governed by **chord face plastification** or **punching shear**.
- **Near-Matched Transition ($0.85 < \beta < 1.0$)**: Linearly interpolate between plastification/punching at $\beta = 0.85$ and sidewall limit states at $\beta = 1.0$, while checking uneven branch load distribution ($b_{eoi}$).
- **Matched Connections ($\beta = 1.0$)**: Branch webs align flush with chord sidewalls. Classified as **Fully Restrained (FR)** per AISC Sec. B3.4b(a). Governed by **chord sidewall yielding/crippling/buckling** (Sec. J10) and **branch uneven load distribution ($b_{eoi}$)**.
- **Inclined Interface Force Resolution ($30^\circ \le \theta \le 90^\circ$)**:
  $$F_\perp = P_r \sin\theta + V_{ry} \cos\theta, \qquad F_\parallel = V_{ry} \sin\theta - P_r \cos\theta$$
  $$F_{flange,max} = \frac{|M_{r\text{-}ip}|}{(H_b - t_b)\sin\theta} + \frac{|F_\perp|}{2}\left(\frac{2 B_b t_b}{A_{g,b}}\right)$$
- **Limits of Applicability (Table K4.2A)**: $\theta \ge 30^\circ$, $B/t \le 35$, $H/t \le 35$, $B_b/t_b \le 35$ and $\le 1.25\sqrt{E/F_{yb}}$, $\beta \ge 0.25$, $0.5 \le H_b/B_b, H/B \le 2.0$, $F_y \le 52\text{ ksi}$, $F_y / F_u \le 0.80$ (both ASTM A500 Gr. C and A1085 satisfy).

---

## 4. Step-by-Step Calculation Procedure (Dual LRFD & ASD)

### Step 1: Primary Member Strength & Combined Interaction (Ch. D–H)
Verify both the branch HSS beam and chord HSS column outside the connection region using $t = 0.93 t_{nom}$ (A500) or $1.00 t_{nom}$ (A1085):
- Flexure (Sec. F7, $\phi_b = 0.90, \Omega_b = 1.67$), Shear (Sec. G4, $\phi_v = 0.90, \Omega_v = 1.67$), Axial (Sec. D2/E3, $\phi_c = 0.90, \Omega_c = 1.67$), and Combined Interaction (Eqs. H1-1a & H1-1b).

### Step 2: Chord Stress Interaction Factor ($Q_f$) & Effective Widths ($B_{ep}, b_{eoi}$)
- If chord connecting face is in **tension**: $Q_f = 1.00$.
- If chord connecting face is in **compression**, compute utilization ratio $U$ per AISC Eq. K3-12 (note: in ASD, scale $P_{a,o}, M_{a,o}$ by $0.60 F_y$ for conservative equivalence with LRFD, or apply literal Eq. K3-12):
  $$U = \left|\frac{P_{ro}}{F_y A_g} + \frac{M_{ro}}{F_y S}\right| \quad \text{(Code Literal)} \qquad \text{or} \qquad U_{ASD,cons} = \left|\frac{P_{a,o}}{0.60 F_y A_g} + \frac{M_{a,o}}{0.60 F_y S}\right|$$
  $$Q_f = 1.30 - 0.40 \left(\frac{U}{\beta}\right) \le 1.00$$
- **Effective Widths (Sec. K1.1, Eq. K1-1)**:
  $$B_{ep} = \frac{10 B_b}{B / t} \le B_b, \qquad b_{eoi} = \frac{10}{B / t} \left(\frac{F_y t}{F_{yb} t_b}\right) B_b \le B_b$$

### Step 3: Axial Force Limit States ($P_c$, `AISC360-22_Table_K3.2` & Sec. J10)
1. **Chord Wall Plastification ($\beta \le 0.85$; $\phi = 1.00, \Omega = 1.50$)**:
   $$P_n \sin\theta = F_y t^2 \left[\frac{2\eta}{1-\beta} + \frac{4}{\sqrt{1-\beta}}\right] Q_f$$
2. **Chord Face Punching Shear ($0.85 < \beta \le 1 - 2t/B$; $\phi = 0.95, \Omega = 1.58$)**:
   $$P_n \sin\theta = 0.60 F_y t \left(\frac{2 H_b}{\sin\theta} + 2 B_{ep}\right)$$
3. **Chord Sidewall Local Yielding ($\beta = 1.0$; $\phi = 1.00, \Omega = 1.50$, Sec. J10.2 with $k = 1.5t$ or $t$)**:
   $$P_n \sin\theta = 2 F_y t \left(5k + \frac{H_b}{\sin\theta}\right)$$
4. **Chord Sidewall Local Crippling ($\beta = 1.0$ in compression; $\phi = 0.75, \Omega = 2.00$, Sec. J10.3)**:
   $$P_n \sin\theta = 1.60 t^2 \left[1 + \frac{3 H_b}{H \sin\theta}\right] \sqrt{E F_y} \, Q_f$$
5. **Chord Sidewall Compression Buckling ($\beta = 1.0$ Cross-Joints; $\phi = 0.90, \Omega = 1.67$, Sec. J10.5)**:
   $$P_n \sin\theta = \left(\frac{48 t^3 \sqrt{E F_y}}{H - 3t}\right) Q_f$$
6. **Branch Uneven Load Distribution (All $\beta$; $\phi = 0.95, \Omega = 1.58$)**:
   $$P_n = F_{yb} t_b (2 H_b + 2 b_{eoi} - 4 t_b)$$

### Step 4: In-Plane & Out-of-Plane Moment Limit States (`AISC360-22_Table_K4.2`)
1. **Stepped Connections ($\beta \le 0.85$) — Chord Wall Plastification ($\phi = 1.00, \Omega = 1.50$)**:
   $$M_{n\text{-}ip} \sin\theta = F_y t^2 H_b \left[\frac{1}{2\eta} + \frac{2}{\sqrt{1-\beta}} + \frac{\eta}{1-\beta}\right] Q_f$$
   $$M_{n\text{-}op} \sin\theta = F_y t^2 \left[\frac{H_b (1+\beta)}{2(1-\beta)\sin\theta} + \sqrt{\frac{2 B^2 (1+\beta)}{1-\beta}}\right] Q_f$$
2. **Chord Face Punching Shear (Out-of-Plane, $B_b < B - 2t$; $\phi = 0.95, \Omega = 1.58$)**:
   $$M_{n\text{-}op} \sin\theta = 0.60 F_y t B_b \left(\frac{H_b}{\sin\theta} + B_{ep}\right)$$
3. **Matched / Near-Matched Connections ($0.85 < \beta \le 1.0$)**:
   - **Local Yielding of Chord Sidewalls** ($\phi = 1.00, \Omega = 1.50$, $F_y^* = F_y$ for T-/Y-conn., $0.80 F_y$ for Cross-conn.):
     $$M_{n\text{-}ip} \sin\theta = 0.50 F_y^* t \left(\frac{H_b}{\sin\theta} + 5t\right)^2, \qquad M_{n\text{-}op} \sin\theta = F_y^* t (B - t)\left(\frac{H_b}{\sin\theta} + 5t\right)$$
   - **Discrete Flange-Force Sidewall Check ($\beta = 1.0$, Sec. J10.2 / J10.3 / J10.5)**: Verify $F_{flange,max}$ against sidewall yielding ($2 F_y t (t_b + 5k)$), crippling, and cruciform buckling ($\frac{48 t^3 \sqrt{E F_y}}{H - 3t} Q_f$).
   - **Uneven Load Distribution in Branch** ($\phi = 0.95, \Omega = 1.58$):
     $$M_{n\text{-}ip} = F_{yb} \left[Z_{b\text{-}ip} - \left(1 - \frac{b_{eoi}}{B_b}\right) B_b H_b t_b\right], \qquad M_{n\text{-}op} = F_{yb} \left[Z_{b\text{-}op} - 0.50\left(1 - \frac{b_{eoi}}{B_b}\right)^2 B_b^2 t_b\right]$$
   - **Chord Distortional Failure (Out-of-Plane Only)** ($\phi = 1.00, \Omega = 1.50$):
     $$M_{n\text{-}op} = 2 F_y t \left[H_b t + \sqrt{B H t (B + H)}\right]$$

### Step 5: Combined Axial, In-Plane & Out-of-Plane Moment Interaction (Sec. K4.3)
$$\frac{P_r}{P_c} + \left(\frac{M_{r\text{-}ip}}{M_{c\text{-}ip}}\right)^2 + \frac{M_{r\text{-}op}}{M_{c\text{-}op}} \le 1.00$$

### Step 6: Throat-Weighted Weld Group & Base Metal Verification (Sec. K5, Table K5.1 & Sec. J2 / J4)
- **No Directional Increase**: Do **not** apply $(1.0 + 0.50\sin^{1.5}\theta)$ to fillet welds at rectangular HSS ends (Sec. J2.4(b)(2)).
- **Throat-Weighted Effective Properties ($\eta_w = E_{flange} / E_{web}$)**: For web fillet throat $E_{web} = 0.7071 w$ and flange groove/flare-bevel throat $E_{flange} \le \min(E_{spec}, t_b, \frac{5}{8}t_{nom})$ with flat web weld length $h_w = (H_b - 4 t_{nom,b})/\sin\theta$ (or $H_b/\sin\theta$ if wrapped all around):
  $$L_{e,eq} = 2 h_w + 2 \eta_w b_{eoi}, \qquad S_{ip,eq} = \frac{h_w^2}{3} + \eta_w b_{eoi} h_w, \qquad S_{op,eq} = h_w B_b + \frac{\eta_w}{3}\left[B_b^2 - \frac{(B_b - b_{eoi})^3}{B_b}\right]$$
  $$I_{wx,eq} = S_{ip,eq}\left(\frac{h_w}{2}\right), \qquad I_{wy,eq} = S_{op,eq}\left(\frac{B_b}{2}\right), \qquad J_{w,eq} = I_{wx,eq} + I_{wy,eq}$$
- **Resultant Weld Stress vs. Available Strength ($\phi_w = 0.75, \Omega_w = 2.00$)**:
  $$q_n = \frac{|F_\perp|}{L_{e,eq}} + \frac{|M_{r\text{-}ip}|}{S_{ip,eq}} + \frac{|M_{r\text{-}op}|}{S_{op,eq}}, \qquad q_{vy} = \frac{|F_\parallel|}{2 h_w} + \frac{|T_r|(B_b/2)}{J_{w,eq}}, \qquad q_{vz} = \frac{|V_{rz}|}{2\eta_w b_{eoi}} + \frac{|T_r|(h_w/2)}{J_{w,eq}}$$
  $$q_{r,max} = \sqrt{q_n^2 + q_{vy}^2 + q_{vz}^2} \le q_{c,web} = 0.45 F_{EXX} E_{web} \; \text{(LRFD)} \quad \text{or} \quad 0.30 F_{EXX} E_{web} \; \text{(ASD)}$$
- **Base Metal Shear Yielding & Rupture (Sec. J4.2)**: Check $0.60 F_y t_{min}$ ($\phi=1.00, \Omega=1.50$) and $0.60 F_u t_{min}$ ($\phi=0.75, \Omega=2.00$) on both branch and chord walls.

### Step 7: Chord Panel Zone Shear & Global Torsion Interaction (Sec. G4 & Sec. H3)
- **Panel Zone Shear (Sec. G4)**: $V_{panel} = \frac{|\Delta M_{r\text{-}ip}|\sin\theta}{H - t} + |F_\parallel| \le V_{c,chord} = \phi_v (0.60 F_y A_{w,chord} C_{v2})$ ($\phi_v = 0.90, \Omega_v = 1.67$).
- **Torsion & Combined Interaction (Sec. H3, Eq. H3-6)**: When $T_{r,chord}/T_c > 0.20$ (e.g., eccentric one-sided T-joint), compute $C = 2(B-t)(H-t)t - 4.5(4-\pi)t^3$, $T_n = 0.60 F_y C$ ($\phi_T = 0.90, \Omega_T = 1.67$), and check:
  $$\left(\frac{P_{r,chord}}{P_c} + \frac{M_{rx,chord}}{M_{cx}} + \frac{M_{ry,chord}}{M_{cy}}\right) + \left(\frac{V_{r,chord}}{V_c} + \frac{T_{r,chord}}{T_c}\right)^2 \le 1.00$$

---

## 5. Limit States Summary Table

| Limit State | Applicability | $\phi$ (LRFD) | $\Omega$ (ASD) | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Chord Wall Plastification** | $\beta \le 0.85$ | $1.00$ | $1.50$ | AISC Table K3.2 / K4.2 |
| **Chord Face Punching Shear** | $0.85 < \beta \le 1 - 2t/B$ | $0.95$ | $1.58$ | AISC Table K3.2 / K4.2 |
| **Chord Sidewall Local Yielding** | $\beta = 1.0$ | $1.00$ | $1.50$ | AISC Table K3.2 / K4.2 / J10.2 |
| **Chord Sidewall Crippling / Buckling** | $\beta = 1.0$ (Comp.) | $0.75 / 0.90$ | $2.00 / 1.67$ | AISC Sec. J10.3 & J10.5 |
| **Branch Uneven Load ($b_{eoi}$)** | $0.85 \le \beta \le 1.0$ | $0.95$ | $1.58$ | AISC Table K3.2 / K4.2 |
| **Chord Distortional Failure** | Unbraced $M_{op}$ | $1.00$ | $1.50$ | AISC DG 24 Ch. 10 |
| **Combined $P$–$M_{ip}$–$M_{op}$** | All HSS-to-HSS | — | — | AISC Sec. K4.3 ($\le 1.00$) |
| **Throat-Weighted Weld / Base Metal** | All Welds | $0.75 / 1.00$ | $2.00 / 1.50$ | AISC Sec. K5, J2.5, J4.2 |
| **Chord Torsion Interaction** | $T_r / T_c > 0.20$ | — | — | AISC Sec. H3, Eq. H3-6 ($\le 1.00$) |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Use $t_{des} = 0.93 t_{nom}$ for ERW HSS (AISC Sec. B4.2)**: For ASTM A500 Gr. C ERW HSS, always use $0.93 t_{nom}$ in all Chapter K formulas (whereas ASTM A1085 uses $1.00 t_{nom}$).
2. **Matched Width Flare-Bevel Groove Welds ($\beta = 1.0$)**: Detail flare-bevel groove welds along the two longitudinal edges where the branch meets the chord corner radii ($E = \frac{5}{8} t_{nom}$ unless WPS-qualified); control flush grinding ($G$) so base metal is not reduced below $t_{des}$.
3. **No Directional Strength Enhancement**: Never apply $(1.0 + 0.50\sin^{1.5}\theta)$ to fillet welds on rectangular HSS ends (Sec. J2.4(b)(2)).
4. **PR vs. FR Modeling**: Unstiffened stepped joints ($\beta < 1.0$) classify as Partially Restrained (PR); matched joints ($\beta = 1.0$) classify as Fully Restrained (FR).

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Check an orthogonal ($\theta = 90^\circ$) T-connection between an **`HSS8x6x1/4` branch beam** ($H_b = 8", B_b = 6", t_b = 0.233", Z_{xb} = 17.7\text{ in.}^3$) and an **`HSS8x8x3/8` chord column** ($H = 8", B = 8", t = 0.349", A_g = 10.4\text{ in.}^2$, ASTM A500 Gr. C, $F_y = 50\text{ ksi}$):
- **Applied In-Plane Moment**: $M_{u\text{-}ip} = 240\text{ kip-in.}$ (LRFD), $M_{a\text{-}ip} = 160\text{ kip-in.}$ (ASD). Chord compression $P_{uo} = 100\text{ kips}$ ($U = 100 / (50 \times 10.4) = 0.192$).
1. **Geometry & $Q_f$**: $\beta = 6 / 8 = 0.75 \le 0.85$; $\eta = 8 / 8 = 1.00$; $Q_f = 1.30 - 0.40(0.192 / 0.75) = 1.198 \implies 1.00$.
2. **Chord Wall Plastification (Table K4.2, $\beta = 0.75 \le 0.85$)**:
   $$M_{n\text{-}ip} = 50 \times (0.349)^2 \times 8.0 \times \left[\frac{1}{2(1.0)} + \frac{2}{\sqrt{1 - 0.75}} + \frac{1.0}{1 - 0.75}\right] \times 1.00 = 48.72 \times 8.50 = 414.1\text{ kip-in.}$$
   - **LRFD**: $\phi M_{n\text{-}ip} = 1.00 \times 414.1 = 414.1\text{ kip-in.} \ge 240\text{ kip-in.} \quad (D/C = 0.580) \implies \textbf{OK}$.
   - **ASD**: $M_{n\text{-}ip}/\Omega = 414.1 / 1.50 = 276.1\text{ kip-in.} \ge 160\text{ kip-in.} \quad (D/C = 0.580) \implies \textbf{OK}$.
