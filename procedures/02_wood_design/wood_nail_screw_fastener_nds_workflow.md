# Calculation Procedure: Nail (Common, Box, Sinker) & Wood Screw Connections (ANSI/AWC NDS 2024)

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration

* **Connection Types Covered**:

  1. **Wood-to-Wood Single & Double Shear Nailed / Screwed Joints**: Framing joints, built-up columns/beams, ledger straps, blocking, and wood structural panel (plywood/OSB) sheathing-to-framing connections using ASTM F1667 Common, Box, or Sinker steel wire nails or ANSI/ASME B18.6.1 wood screws.

  2. **Steel-to-Wood Single Shear Joints**: Cold-formed steel straps, hurricane ties, framing angles, and joist hangers ($20	ext{ ga}$ to $3	ext{ ga}$ steel side plates) fastened with nails or wood screws.

  3. **Toe-Nailed & End-Grain Connections**: Stud-to-plate and rafter-to-plate toe-nailing (installed at $30^\circ$ to member face starting at \$rac{1}{3} L$ from member end per [NDS Figure 12A](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).

* **Governing Codes & Standards**:

  * [ANSI/AWC NDS-2024 Chapter 11 (Mechanical Connections)](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)

  * [ANSI/AWC NDS-2024 Chapter 12 (Dowel-Type Fasteners: Sections 12.1.5, 12.1.6, 12.2.2, 12.2.3, 12.3, 12.4, 12.5.4)](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)

  * [ANSI/AWC NDS-2024 Appendix I (Table I1), Appendix L (Tables L3 & L4), and Appendix N (LRFD)](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)

* **Required CSV Database Tables**:

  * `database/nds_wood/v2024/NDS-2024_Table_11.3.1.csv` & `NDS-2024_Table_11.3.3.csv`

  * `database/nds_wood/v2024/NDS-2024_Table_12.2B.csv` (Wood Screw Withdrawal $W$)

  * `database/nds_wood/v2024/NDS-2024_Table_12.2C.csv` (Nail & Spike Withdrawal $W$)

  * `database/nds_wood/v2024/NDS-2024_Table_12.3.3.csv` & `NDS-2024_Table_12.3.3A.csv` ($F_e, G$)

  * `database/nds_wood/v2024/NDS-2024_Table_12L.csv` (Wood Screw Wood-to-Wood $Z$) & `NDS-2024_Table_12M.csv` (Wood Screw Steel-to-Wood $Z$)

  * `database/nds_wood/v2024/NDS-2024_Table_12N.csv` (Nail Wood-to-Wood $Z$) & `NDS-2024_Table_12P.csv` (Nail Steel-to-Wood $Z$)

  * `database/nds_wood/v2024/NDS-2024_Table_L2_L3_L4_I1.csv` (Nail & Wood Screw Dimensions $D, D_r, L, D_H, F_{yb}$)

### 1.2 Load Path & Force Transfer Mechanism

1. **Lateral Shear Transfer (**$Z'$**)**: Because nails and wood screws with $D < 1/4	ext{ in.}$ have isotropic dowel bearing strength ($F_{e\parallel} = F_{e\perp} = 16,600 G^{1.84}$ per [NDS Table 12.3.3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)), their lateral capacity $Z$ is independent of the angle of load to grain ($heta$).

2. **Axial Withdrawal Transfer (**$W'$**)**: Resisted by friction/thread shear in side grain ($W' \cdot p$), limited by head pull-through ($W'_H$) in the side member. Nails installed in end grain have **zero** permitted withdrawal capacity ([NDS Section 12.2.3.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).

## Section 2: Load Combinations & Internal Forces at the Critical Section

* Evaluate governing ASD ([ASCE 7-22 Section 2.4](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)) and LRFD ([ASCE 7-22 Section 2.3](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)) load combinations from `ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv`.

* For a fastener group of $N$ identical nails or wood screws ($D < 1/4	ext{ in.}$, where $C_g = 1.0$):
  

  $$
  v_{	ext{req}} = rac{V_{	ext{tot}}}{N}, \qquad t_{	ext{req}} = rac{T_{	ext{tot}}}{N}
  $$

## Section 3: Primary Member Verification

* Verify that wood side member thickness $t_s$ and main member thickness $t_m$ accommodate the fastener length $L$ without splitting, and check net member tension/shear stresses at the connection zone per [NDS Chapter 3](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk).

## Section 4: Sequential Connection / Limit State Checks Along the Load Path

### Step 4.1: Fastener Dimensions, Penetration ($p$), and Penetration Depth Factor ($C_d$)

1. Retrieve $D, D_r, L, D_H, F_{yb}$ from `NDS-2024_Table_L2_L3_L4_I1.csv` ([NDS Appendix Tables L3, L4, and I1](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)).

2. **Main Member Penetration (**$p$**)**:

   * **Standard Face Nailing / Screwing**:
     

     $$
     p = L - t_s \ge p_{\min} = 6D
     $$

   * **Toe-Nailing** (installed at $30^\circ$ to face starting at $L/3$ from end per [NDS Figure 12A](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

     * Equivalent side member bearing length: $\ell_s = rac{L}{3}$

     * Vertical projected penetration into main member: $p_{	ext{toe}} = L \cos 30^\circ - rac{L}{3} = 0.533 L$

3. **Penetration Depth Factor (**$C_d$**)** ([NDS Sections 12.1.5.5 & 12.1.6.4](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

   * Full tabulated lateral design value requires $p \ge 10D$.

   * For $6D \le p < 10D$:
     

     $$
     C_d = rac{p}{10D}
     $$

   * For $p < 6D$: $Z = 0$ (Not Permitted).

### Step 4.2: Reference Lateral Design Value ($Z$)

1. **Tabulated Lookup**:

   * Wood Screws (Wood-to-Wood): `NDS-2024_Table_12L.csv`

   * Wood Screws (Steel-to-Wood): `NDS-2024_Table_12M.csv`

   * Common/Box/Sinker Nails (Wood-to-Wood): `NDS-2024_Table_12N.csv`

   * Common/Box/Sinker Nails (Steel-to-Wood): `NDS-2024_Table_12P.csv`

2. **Exact Yield Limit Equations** ([NDS Table 12.3.1A & 12.3.1B](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

   * For $D < 0.25	ext{ in.}$, the reduction term is $R_d = K_D$, where:
     

     $$
     K_D = egin{cases} 2.2 & 	ext{for } D \le 0.17	ext{ in.} \ 10D + 0.5 & 	ext{for } 0.17	ext{ in.} < D < 0.25	ext{ in.} \end{cases}
     $$

   * Use $D_{	ext{calc}} = D_r$ for rolled thread wood screws and $D_{	ext{calc}} = D$ for smooth-shank nails, with dowel bearing length in main member $\ell_m = p - 2D$ (deducting tapered tip length $E = 2D$ for bearing resistance) and $F_e = 16,600 G^{1.84}$ from `NDS-2024_Table_12.3.3.csv`.

### Step 4.3: Adjustment Factors & Adjusted Lateral Capacity ($Z'$)

Per [NDS Table 11.3.1](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk):

* **ASD**:
  

  $$
  Z'_{	ext{ASD}} = Z \cdot C_D \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta \cdot C_d \cdot C_{eg} \cdot C_{tn}
  $$

* **LRFD**:
  

  $$
  Z'_{	ext{LRFD}} = Z \cdot 3.32 \cdot 0.65 \cdot \lambda \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta \cdot C_d \cdot C_{eg} \cdot C_{tn}
  $$

* Where:

  * $C_g = 1.00$ and $C_\Delta = 1.00$ for $D < 1/4	ext{ in.}$ when minimum anti-splitting spacing is provided ([NDS Section 12.5.1.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).

  * **End-Grain Factor (**$C_{eg}$**)**: $C_{eg} = 0.67$ for nails or wood screws driven into end grain parallel to wood fibers; $1.00$ in side grain.

  * **Toe-Nail Factor (**$C_{tn}$**)** ([NDS Section 12.5.4](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

    * Lateral loading of toe-nailed connections: $C_{tn} = 0.83$

    * Withdrawal loading of toe-nailed connections: $C_{tn} = 0.67$ (and $C_M$ does not apply to toe-nails in withdrawal per Table 11.3.1 Footnote 2).

### Step 4.4: Reference & Adjusted Withdrawal ($W'$) and Head Pull-Through ($W'_H$)

1. **Reference Withdrawal (**$W$**,** $ext{lbs/in.}$**)**:

   * **Wood Screws** ([NDS Section 12.2.2 Eq. 12.2-2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk), `NDS-2024_Table_12.2B.csv`):
     

     $$
     W = 2850 \cdot G^2 \cdot D \quad (	ext{lbs/in. of thread penetration } p_t)
     $$

     
     *(Note: Wood screws shall NOT be loaded in withdrawal from end grain per [NDS Section 12.2.2.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).*

   * **Smooth Shank Nails** ([NDS Section 12.2.3 Eq. 12.2-3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk), `NDS-2024_Table_12.2C.csv`):
     

     $$
     W = 1380 \cdot G^{5/2} \cdot D \quad (	ext{lbs/in. of penetration } p)
     $$

     
     *(Note: Nails shall NOT be loaded in withdrawal from end grain per [NDS Section 12.2.3.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).*

2. **Head Pull-Through (**$W_H$**)** ([NDS Section 12.2.5 Eq. 12.2-6a/6b & Table 12.2F](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   

   $$
   W_H = 690 \cdot \pi \cdot D_H \cdot G^2 \cdot t_{ns} \le 690 \cdot \pi \cdot D_H^2 \cdot G^2 \cdot (2.5) \quad (	ext{lbs})
   $$

   
   where $D_H$ is fastener head diameter and $t_{ns}$ is net side member thickness.

3. **Combined Lateral & Withdrawal Loading**:

   * **Wood Screws** ([NDS Section 12.4.1 Eq. 12.4-1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
     

     $$
     Z'_lpha = rac{(W' p_t) \cdot Z'}{(W' p_t)\cos^2lpha + Z'\sin^2lpha}
     $$

   * **Nails and Spikes** ([NDS Section 12.4.2 Eq. 12.4-2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
     

     $$
     Z'_lpha = rac{(W' p) \cdot Z'}{(W' p)\coslpha + Z'\sinlpha}
     $$

## Section 5: Supporting Member / Global Substrate Verification

* Verify that wood framing members have sufficient edge and end thickness to prevent splitting during driving, and verify steel strap/hanger net tension and shear capacities per AISC 360 / AISI S100 or manufacturer ICC-ES evaluation report.

## Section 6: Mandatory Detailing & Construction Notes

1. **Lead Holes for Wood Screws** ([NDS Section 12.1.5.2 & 12.1.5.3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

   * Where $G > 0.60$, bore shank hole $= D$ and thread lead hole $= 0.90 D_r$ (for withdrawal) or $0.70 D_r$ (for lateral). For $G \le 0.60$, lead holes are optional unless required to prevent splitting near edges/ends.

2. **Minimum Anti-Splitting Nail/Screw Spacing** ([NDS Commentary C12.5.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):

   * Without predrilled holes: End distance $\ge 15D$, spacing in row $\ge 15D$, edge distance $\ge 2.5D$, spacing between rows $\ge 5D$.

   * With predrilled holes: End distance $\ge 10D$, spacing in row $\ge 10D$, edge distance $\ge 2.5D$, spacing between rows $\ge 3D$.

3. **Wet Service Factor Warning for Nails in Withdrawal**: Per `NDS-2024_Table_11.3.3.csv`, smooth-shank nails driven into unseasoned wood ($>19\%$) that seasons in service ($\le 19\%$), or seasoned wood exposed to wet service ($>19\%$), suffer a severe withdrawal reduction factor of $C_M = 0.25$ (use Ring-Shank nails where $C_M = 1.0$, or wood/lag screws where $C_M = 0.70$).

## Section 7: Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation | 
| ----- | ----- | ----- | ----- | 
| **1** | Penetration Depth Check | NDS-2024 Sec. 12.1.5.5 & 12.1.6.4 | $p = L - t_s \ge 6D$; $C_d = \min(1.0, p / 10D)$ | 
| **2** | Reference Lateral Value ($Z$) | NDS-2024 Tables 12.3.1A, 12L, 12M, 12N, 12P | $Z = \min(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{II}}, Z_{	ext{III}_m}, Z_{	ext{III}_s}, Z_{	ext{IV}})$ | 
| **3** | Adjusted Lateral Capacity ($Z'$) | NDS-2024 Table 11.3.1 & Sec. 12.5.4 | $v_{	ext{req}} \le Z \cdot C_D C_M C_t C_d C_{eg} C_{tn}$ (ASD) | 
| **4** | Adjusted Withdrawal & Pull-Through | NDS-2024 Sec. 12.2.2, 12.2.3, 12.2.5, Table 12.2B/C/F | $t_{	ext{req}} \le \min(W' p,\ W'_H)$ ($W'=0$ in end grain) | 
| **5** | Combined Load Interaction ($Z'_lpha$) | NDS-2024 Sec. 12.4.1 (Screws) & Sec. 12.4.2 (Nails) | Screws: Eq. (12.4-1); Nails: $Z'_lpha = rac{(W' p) Z'}{(W' p)\coslpha + Z'\sinlpha}$ | 
