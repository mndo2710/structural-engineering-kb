# CMU Masonry Anchorage & Out-of-Plane Breakout Design Procedure (TMS 402-22 Ch. 8 & 9)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 21.
  - **TMS 402/602-22**: *Building Code Requirements and Specification for Masonry Structures*, Section 6.1.6 (Anchor Bolt Placement), Chapter 8 Section 8.1.3 (Allowable Stress Design of Anchor Bolts), and Chapter 9 Section 9.1.6 (Strength Design of Anchor Bolts) ([TMS 402 Masonry Anchor Bolt Guide](https://www.scribd.com/document/450073931/Anchor-pdf)).
  - **Simpson Strong-Tie Masonry Anchors (C-A-2023)**: [Titen HD in CMU (ICC-ES ESR-1056)](https://www.strongtie.com/screwanchors_mechanicalanchoringproducts/thd_anchor/p/titen-hd) & [SET-3G in CMU (ICC-ES ESR-4844)](https://www.strongtie.com/epoxyanchoringadhesives_adhesives/set-3g_adhesive/p/set-3g).
- **Referenced Repository Databases**:
  - `database/aci_318_tms_402/tms_402_22/TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv`

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $b_{af}, b_{vf}$ | Applied ASD (or Strength Design) tension ($b_{af}$) and shear ($b_{vf}$) per anchor | $\text{lbs}$ | ASCE 7-22 Load Combinations |
| $t_{wall}, f'_m$ | Actual CMU wall thickness ($7.625"$ for $8"$ CMU) and compressive strength $f'_m$ | $\text{in.}, \text{psi}$ | `TMS402-22_Masonry_...csv` ($f'_m = 2,000\text{ psi}$) |
| $d_b, A_b, f_y$ | Anchor bolt diameter, effective tensile stress area ($A_{se,N}$), and yield strength | $\text{in.}, \text{in.}^2, \text{psi}$ | `ASTM_F1554_...csv` ($f_y = 36,000\text{ psi}$) |
| $l_b$ | Effective embedment length of anchor bolt (to bearing surface of head/nut or hook) | $\text{in.}$ | TMS 402 Sec. 6.1.6 ($l_b \ge \max(4d_b, 2")$) |
| $l_{be}$ | Edge distance measured in direction of shear load from anchor center to free edge | $\text{in.}$ | Connection Detailing |
| $e_b$ | Projected leg extension of bent-bar (J/L) anchor bolt | $\text{in.}$ | Only for bent-bar bolts |

---

## 3. Projected Breakout Areas ($A_{pt}, A_{pv}$) for Face-Mounted vs. Top-of-Wall Anchors

### 3.1 Tension Breakout Area ($A_{pt}$, TMS 402 Eq. 8-4 / Eq. 9-4)
- **Full Unobstructed $45^\circ$ Cone**: $A_{pt,0} = \pi \cdot l_b^2$
- **Face-Mounted Anchor on CMU Wall**: Usually $l_b \le t_{wall} - 1.5"$ ($l_b \approx 5.5"$ to $6.0"$ in $8"$ CMU). If anchor spacing $s < 2 l_b$ or distance to wall top/end $< l_b$, deduct the overlapping circular segment:
  $$A_{overlap} = 2 l_b^2 \arccos\left(\frac{s}{2 l_b}\right) - \frac{s}{2}\sqrt{4 l_b^2 - s^2}$$
- **Top-of-Wall (Sill Plate / Holdown) Anchor in Narrow CMU Wall ($t_{wall} < 2 l_b$)**:
  - When $l_b > t_{wall}/2$ (e.g., $l_b = 10"$ in an $8"$ CMU wall where $t = 7.625"$), the $45^\circ$ breakout cone is **truncated on both sides** by the front and back faces of the CMU wall!
  - Exact chord angle $\theta = \arcsin\left(\frac{t_{wall}/2}{l_b}\right)$ (in radians):
    $$A_{pt,top\text{-}wall} = 2 l_b^2 \theta + t_{wall} \sqrt{l_b^2 - \left(\frac{t_{wall}}{2}\right)^2} \approx t_{wall} \cdot (2 l_b) \quad (\text{rectangular strip approximation when } l_b \gg t_{wall}/2)$$

### 3.2 Shear Breakout Area ($A_{pv}$, TMS 402 Eq. 8-6 / Eq. 9-10)
- **Half-Cone Radiating from Anchor to Free Edge at Distance $l_{be}$**:
  $$A_{pv,0} = \frac{\pi \cdot l_{be}^2}{2}$$
  Truncate $A_{pv}$ if wall thickness $t_{wall} < 2 l_{be}$ or if embedment depth $l_b < l_{be}$.

---

## 4. Step-by-Step Calculation Procedure (Dual ASD Ch. 8 & Strength Design Ch. 9)

### Step 1: Anchor Bolts in Axial Tension ($B_a$ ASD / $\phi B_{an}$ SD)
Evaluate the **minimum** of the three tension limit states (`TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv`):
1. **Masonry Breakout**:
   - **ASD (Eq. 8-2)**: $B_{ab} = 1.25 \cdot A_{pt} \cdot \sqrt{f'_m}$
   - **Strength Design (Eq. 9-1)**: $\phi B_{anb} = 0.50 \cdot \left(4.0 \cdot A_{pt} \cdot \sqrt{f'_m}\right) = 2.00 \cdot A_{pt} \cdot \sqrt{f'_m}$
2. **Anchor Steel Yielding**:
   - **ASD (Eq. 8-3)**: $B_{as} = 0.60 \cdot A_b \cdot f_y$
   - **Strength Design (Eq. 9-2)**: $\phi B_{ans} = 0.90 \cdot A_b \cdot f_y$
3. **Anchor Pullout (Bent-Bar J/L Bolts Only — Headed Bolts Exempt)**:
   - **ASD (Eq. 8-5)**: $B_{ap} = 1.5 f'_m e_b d_b + 300 \pi (l_b + e_b + d_b) d_b$
   - **Strength Design (Eq. 9-3)**: $\phi B_{anp} = 0.65 \cdot \left[1.5 f'_m e_b d_b + 300 \pi (l_b + e_b + d_b) d_b\right]$
- **Governing Tension Capacity**: $B_a = \min(B_{ab}, B_{as}, B_{ap})$ [ASD] or $\phi B_{an} = \min(\phi B_{anb}, \phi B_{ans}, \phi B_{anp})$ [SD].

### Step 2: Anchor Bolts in Shear ($B_v$ ASD / $\phi B_{vn}$ SD)
Evaluate the **minimum** of the four shear limit states:
1. **Masonry Shear Breakout** (where $l_{be} < 12 d_b$ or near free edge):
   - **ASD (Eq. 8-7)**: $B_{vb} = 0.625 \cdot A_{pv} \cdot \sqrt{f'_m}$
   - **Strength Design (Eq. 9-5)**: $\phi B_{vnb} = 0.50 \cdot \left(4.0 \cdot A_{pv} \cdot \sqrt{f'_m}\right) = 2.00 \cdot A_{pv} \cdot \sqrt{f'_m}$
2. **Masonry Shear Crushing**:
   - **ASD (Eq. 8-8)**: $B_{vc} = 580 \cdot \sqrt[4]{f'_m \cdot A_b}$
   - **Strength Design (Eq. 9-6)**: $\phi B_{vnc} = 0.50 \cdot 1750 \cdot \sqrt[4]{f'_m \cdot A_b} = 875 \cdot \sqrt[4]{f'_m \cdot A_b}$
3. **Anchor Shear Pryout**:
   - **ASD (Eq. 8-9)**: $B_{vpry} = 2.0 \cdot B_{ab} = 2.50 \cdot A_{pt} \cdot \sqrt{f'_m}$
   - **Strength Design (Eq. 9-7)**: $\phi B_{vnpry} = 0.50 \cdot (2.0 \cdot B_{anb}) = 4.00 \cdot A_{pt} \cdot \sqrt{f'_m}$
4. **Anchor Steel Shear Yielding**:
   - **ASD (Eq. 8-10)**: $B_{vs} = 0.36 \cdot A_b \cdot f_y$
   - **Strength Design (Eq. 9-8)**: $\phi B_{vns} = 0.90 \cdot (0.60 \cdot A_b \cdot f_y) = 0.54 \cdot A_b \cdot f_y$
- **Governing Shear Capacity**: $B_v = \min(B_{vb}, B_{vc}, B_{vpry}, B_{vs})$ [ASD] or $\phi B_{vn}$ [SD].

### Step 3: Combined Tension and Shear Interaction (Sec. 8.1.3.4 / Sec. 9.1.6.4)
$$\frac{b_{af}}{B_a} + \frac{b_{vf}}{B_v} \le 1.00 \quad [\text{ASD Eq. 8-11}], \qquad \frac{b_{uaf}}{\phi B_{an}} + \frac{b_{uvf}}{\phi B_{vn}} \le 1.00 \quad [\text{SD Eq. 9-9}]$$

---

## 5. Limit States Summary Table

| Limit State | ASD Capacity (TMS 402 Ch. 8) | Strength Design Capacity (TMS 402 Ch. 9) | Reference |
| :--- | :--- | :--- | :--- |
| **Tension Masonry Breakout** | $1.25 A_{pt} \sqrt{f'_m}$ | $0.50 (4.0 A_{pt} \sqrt{f'_m})$ | Eq. 8-2 / Eq. 9-1 |
| **Tension Steel Yielding** | $0.60 A_b f_y$ | $0.90 (A_b f_y)$ | Eq. 8-3 / Eq. 9-2 |
| **Tension Bent-Bar Pullout** | $1.5 f'_m e_b d_b + 300\pi(l_b+e_b+d_b)d_b$ | $0.65 B_{anp}$ | Eq. 8-5 / Eq. 9-3 |
| **Shear Masonry Breakout** | $0.625 A_{pv} \sqrt{f'_m}$ | $0.50 (4.0 A_{pv} \sqrt{f'_m})$ | Eq. 8-7 / Eq. 9-5 |
| **Shear Masonry Crushing** | $580 (f'_m A_b)^{0.25}$ | $0.50 [1750 (f'_m A_b)^{0.25}]$ | Eq. 8-8 / Eq. 9-6 |
| **Shear Anchor Pryout** | $2.0 B_{ab}$ | $0.50 (2.0 B_{anb})$ | Eq. 8-9 / Eq. 9-7 |
| **Shear Steel Yielding** | $0.36 A_b f_y$ | $0.90 (0.60 A_b f_y)$ | Eq. 8-10 / Eq. 9-8 |
| **Combined Tension + Shear** | $(b_{af}/B_a) + (b_{vf}/B_v) \le 1.00$ | $(b_{uaf}/\phi B_{an}) + (b_{uvf}/\phi B_{vn}) \le 1.00$ | Eq. 8-11 / Eq. 9-9 |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Never Use Bent-Bar (J/L) Bolts for Holdowns in CMU**: Bent-bar pullout ($B_{ap}$, Eq. 8-5) severely limits uplift capacity ($\sim 1,500\text{–}2,300\text{ lbs}$). Always specify **headed anchor bolts** (`ASTM F1554 Gr. 36` or `Simpson PAB`) so Eq. 8-5 is eliminated!
2. **Truncated Cone Area ($A_{pt}$) in Top-of-Wall Holdown Anchors**: Plan checkers reject full $\pi l_b^2$ calculations when $2 l_b > t_{wall}$. Always truncate $A_{pt}$ by the wall thickness $t_{wall}$ ($7.625"$ for $8"$ CMU).
3. **Engage Vertical Wall Rebar When Uplift Exceeds Breakout**: If holdown uplift $T > B_{ab}$ in a top-of-wall anchor, detail the anchor bolt to extend down alongside a vertical CMU bond/jamb bar with confining hairpins/ties so tension transfers directly into the vertical wall reinforcement.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Determine the minimum required embedment length $l_b$ in the top of an **8-inch grouted CMU wall** ($t = 7.625\text{ in.}, f'_m = 2,000\text{ psi}$) for a **`5/8"` dia. headed ASTM F1554 Gr. 36 anchor bolt** ($A_b = 0.226\text{ in.}^2, f_y = 36,000\text{ psi}$) resisting an **ASD truss uplift force of $b_{af} = 2,500\text{ lbs}$** (using a Simpson `HDU4` holdown, interior of wall far from ends):
1. **Steel Yielding Check (TMS 402 Eq. 8-3)**:
   $$B_{as} = 0.60 \times 0.226 \times 36,000 = 4,882\text{ lbs} \ge 2,500\text{ lbs} \quad (D/C = 0.512) \implies \textbf{OK}$$
2. **Required Tension Breakout Area ($A_{pt,req}$, TMS 402 Eq. 8-2)**:
   $$B_{ab} = 1.25 \cdot A_{pt} \cdot \sqrt{2,000} = 55.902 \cdot A_{pt} \ge 2,500\text{ lbs} \implies A_{pt,req} = \frac{2,500}{55.902} = 44.72\text{ in.}^2$$
3. **Solve for Required Embedment $l_b$ in $t = 7.625\text{ in.}$ Wall**:
   - Note that an un-truncated circle of radius $r = t/2 = 3.8125"$ has area $\pi(3.8125)^2 = 45.66\text{ in.}^2 > 44.72\text{ in.}^2$!
   - However, to provide comfortable construction margin and account for top-edge grout cover, try **$l_b = 6.0\text{ in.}$**:
     - Chord angle $\theta = \arcsin(3.8125 / 6.0) = 0.6885\text{ rad}$
     - Truncated cone area:
       $$A_{pt} = 2(6.0)^2(0.6885) + 7.625\sqrt{6.0^2 - 3.8125^2} = 49.57 + 35.33 = 84.90\text{ in.}^2$$
     - Allowable Masonry Breakout Capacity:
       $$B_{ab} = 1.25 \times 84.90 \times \sqrt{2,000} = 4,746\text{ lbs} \ge 2,500\text{ lbs} \quad (D/C = 0.527) \implies \textbf{OK}$$
   - **Specify `5/8"` dia. Headed Anchor Bolt (`F1554 Gr. 36`) with $l_b = 6.0\text{ in.}$ minimum embedment (or $8.0\text{ in.}$ standard)**.
