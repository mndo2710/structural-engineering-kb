# Calculation Procedure: Wood Bolted Connections & Brittle Group Tear-Out (ANSI/AWC NDS 2024)

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Connection Types Covered**:
  1. **Single Shear (Two-Member) Bolted Joints**:
     - Wood-to-Wood (Sawn Lumber, Glulam, or SCL): `Table 12A`, `Table 12C`
     - Wood-to-Steel ($1/4	ext{ in.}$ ASTM A36 side plate): `Table 12B`, `Table 12D`
     - Wood-to-Concrete or Grouted CMU ($f'_c \ge 2,500	ext{ psi}$, anchor embedment $\ge 6.0	ext{ in.}$): `Table 12E` (sill plates, ledger boards, post bases)
  2. **Symmetric Double Shear (Three-Member) Bolted Joints**:
     - Wood Main Member with Two Wood Side Members: `Table 12F`, `Table 12H`
     - Wood Main Member with Two $1/4	ext{ in.}$ ASTM A36 Steel Side Plates (flitch/gusset plates): `Table 12G`, `Table 12I`
     - Slotted Wood Member with Internal Steel Knife Plate: Evaluated directly via Double Shear Yield Limit Equations ([NDS Table 12.3.1A Eq. 12.3-7 to 12.3-10](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).
- **Governing Codes & Standards**:
  - [ANSI/AWC NDS-2024 Chapter 3 (Design Provisions and Equations: Net Section 3.1.2 & Shear at Connections 3.4.3.3)](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Chapter 11 (Mechanical Connections)](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Chapter 12 (Dowel-Type Fasteners: Sections 12.1.3, 12.3, 12.5, Tables 12A–12I)](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Appendix E (Local Stresses in Fastener Groups), Appendix I, Appendix J (Hankinson Formula), Appendix L (Tables L1 & L8), and Appendix N (LRFD)](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)
- **Required CSV Database Tables**:
  - `database/nds_wood/v2024/NDS-2024_Table_11.3.1.csv`, `11.3.3.csv`, `11.3.4.csv`, `11.3.6A.csv`, `11.3.6C.csv`
  - `database/nds_wood/v2024/NDS-2024_Table_12.3.3.csv` & `NDS-2024_Table_12.3.3A.csv`
  - `database/nds_wood/v2024/NDS-2024_Table_12.5.1A.csv` & `NDS-2024_Table_12.5.1B_12.5.1C_12.5.1D_12.5.1E.csv`
  - `database/nds_wood/v2024/NDS-2024_Table_12A.csv` through `NDS-2024_Table_12I.csv`
  - `database/nds_wood/v2024/NDS-2024_Table_L1_L7_L8.csv`

### 1.2 Load Path & Force Transfer Mechanism
1. **Ductile Dowel Bearing & Bolt Yielding ($n \cdot Z'$)**: Shear across the interface is resisted by wood crushing ($F_{em}, F_{es}$) and plastic hinge formation in the bolt ($F_{yb} = 45,000	ext{ psi}$ for SAE J429 Grade 1 / ASTM A307 bolts).
2. **Brittle Wood Fracture Around Bolt Group (`Appendix E`)**: For connections loaded parallel to grain in tension, closely spaced bolts with high dowel capacity ($D \ge 1/2	ext{ in.}$) frequently fail by brittle wood plug shear (**Row Tear-Out $Z'_{RT}$** or **Group Tear-Out $Z'_{GT}$**) or **Net Section Tension Rupture ($Z'_{NT}$)** well before reaching $n \cdot Z'$.
3. **Axial Bolt Tension ($T$)**: Transferred via steel bolt tensile stress area $A_{se}$ and reacted by compression perpendicular to grain ($F'_{c\perp} \cdot C_b$) under standard cut washers (`Table L8`) or steel bearing plates.

## Section 2: Load Combinations & Internal Forces at the Critical Section
- Apply ASD ([ASCE 7-22 Section 2.4](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)) and LRFD ([ASCE 7-22 Section 2.3](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)) load combinations from `ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv`.
- Resolve eccentric shear $V$ and moment $M = V \cdot e$ on a bolt group into parallel-to-grain component $V_\parallel$ and perpendicular-to-grain component $V_\perp$ on the most heavily loaded bolt:
  $$v_{\parallel,i} = rac{P_\parallel}{N} + rac{M \cdot y_i}{\sum (x_j^2 + y_j^2)}, \qquad v_{\perp,i} = rac{V_\perp}{N} + rac{M \cdot x_i}{\sum (x_j^2 + y_j^2)}$$
  $$v_{	ext{req}} = \sqrt{v_{\parallel,i}^2 + v_{\perp,i}^2}, \qquad 	heta = rctan\left(rac{v_{\perp,i}}{v_{\parallel,i}}ight)$$

## Section 3: Primary Member Verification

### 3.1 Net Section Area ($A_{	ext{net}}$) (NDS Section 3.1.2)
- Bolt hole diameter for net section calculation ([NDS Section 12.1.3.2 & Appendix E.6](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)):
  $$D_h = D + rac{1}{16}	ext{ in.} = D + 0.0625	ext{ in.}$$
- Staggered bolts in adjacent rows are treated as occurring at the same critical section if parallel-to-grain stagger spacing is $< 4D$ ([NDS Section 3.1.2.2 & Figure 3A](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)):
  $$A_{	ext{net}} = t \cdot \left(w - n_{	ext{rows,crit}} \cdot D_hight)$$

### 3.2 Effective Depth Shear Check at Eccentric Connections (NDS Section 3.4.3.3)
- Where a bolt group transmits a perpendicular-to-grain reaction $V$ within $5d$ from the support, check reduced member depth $d_e$ (distance from the loaded edge to the furthest bolt row, [NDS Figure 3E](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)):
  $$f_{v,e} = rac{3 V}{2 b d_e} \le F'_v$$

## Section 4: Sequential Connection / Limit State Checks Along the Load Path

### Step 4.1: Reference Lateral Design Value ($Z$) — Single & Double Shear Yield Equations
1. **Dowel Bearing Strengths ($F_{em}, F_{es}$)**:
   - Lookup $F_{e\parallel}$ and $F_{e\perp}$ from `NDS-2024_Table_12.3.3.csv` based on specific gravity $G$ (`NDS-2024_Table_12.3.3A.csv`) and bolt diameter $D$.
   - For loading at angle $	heta$ to grain, compute $F_{e	heta}$ via Hankinson's formula ([NDS Section 12.3.4 & Appendix J](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)):
     $$F_{e	heta} = rac{F_{e\parallel} \cdot F_{e\perp}}{F_{e\parallel} \sin^2	heta + F_{e\perp} \cos^2	heta}$$
   - For ASTM A36 steel side or main plates: $F_e = 87,000	ext{ psi}$ ($1.5 F_u$ where $F_u = 58,000	ext{ psi}$).
   - For Concrete or Grouted CMU ($f'_c \ge 2,500	ext{ psi}$, $t_m \ge 6.0	ext{ in.}$): $F_{em} = 7,500	ext{ psi}$ ([NDS Table 12E Footnote 3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).
2. **Reduction Term ($R_d$)** ([NDS Table 12.3.1B](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk) for $0.25	ext{ in.} \le D \le 1.0	ext{ in.}$, where $K_	heta = 1 + 0.25(	heta_{\max}/90^\circ)$):
   - Modes $	ext{I}_m, 	ext{I}_s$: $R_d = 4.0 K_	heta$
   - Mode $	ext{II}$: $R_d = 3.6 K_	heta$
   - Modes $	ext{III}_m, 	ext{III}_s, 	ext{IV}$: $R_d = 3.2 K_	heta$
3. **Single Shear Yield Modes** ([NDS Table 12.3.1A Eq. 12.3-1 to 12.3-6](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   $$Z_{	ext{single}} = \min\left(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{II}}, Z_{	ext{III}_m}, Z_{	ext{III}_s}, Z_{	ext{IV}}ight)$$
   (Or lookup directly from `NDS-2024_Table_12A.csv` through `12E.csv`).
4. **Symmetric Double Shear Yield Modes** ([NDS Table 12.3.1A Eq. 12.3-7 to 12.3-10](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   $$egin{aligned}
   Z_{	ext{I}_m} &= rac{D \ell_m F_{em}}{R_d} \quad (	ext{Eq. 12.3-7}) \
   Z_{	ext{I}_s} &= rac{2 D \ell_s F_{es}}{R_d} \quad (	ext{Eq. 12.3-8}) \
   Z_{	ext{III}_s} &= rac{2 k_3 D \ell_s F_{em}}{(2 + R_e) R_d} \quad (	ext{Eq. 12.3-9}) \
   Z_{	ext{IV}} &= rac{2 D^2}{R_d} \sqrt{rac{2 F_{em} F_{yb}}{3(1 + R_e)}} \quad (	ext{Eq. 12.3-10})
   \end{aligned}$$
   $$Z_{	ext{double}} = \min\left(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{III}_s}, Z_{	ext{IV}}ight)$$
   (Or lookup directly from `NDS-2024_Table_12F.csv` through `12I.csv`).

### Step 4.2: Group Action Factor ($C_g$) & Geometry Factor ($C_\Delta$)
1. **Exact Algebraic Group Action Factor ($C_g$)** ([NDS Section 11.3.6.1 Eq. 11.3-1](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)):
   $$C_g = \left[rac{m(1 - m^{2n})}{n \left[(1 + R_{EA} m^n)(1 + m) - 1 + m^{2n}ight]}ight] \left(rac{1 + R_{EA}}{1 - m}ight)$$
   where:
   - $n =$ number of bolts in a row
   - $R_{EA} = \min\left(rac{E_s A_s}{E_m A_m},\ rac{E_m A_m}{E_s A_s}ight)$
   - $\gamma = 180,000 D^{1.5}$ (wood-to-wood) or $\gamma = 270,000 D^{1.5}$ (wood-to-metal) ($	ext{lbs/in.}$)
   - $u = 1 + \gamma rac{s}{2}\left(rac{1}{E_m A_m} + rac{1}{E_s A_s}ight)$
   - $m = u - \sqrt{u^2 - 1}$
   *(Alternatively, lookup conservative values from `NDS-2024_Table_11.3.6A.csv` or `11.3.6C.csv`).*
2. **Geometry Factor ($C_\Delta$)** ([NDS Section 12.5.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   - End distance $a$: For parallel-to-grain tension in softwoods, $a_{\min} = 3.5D$ ($C_\Delta = 0.5$) and $a_{	ext{full}} = 7D$ ($C_\Delta = 1.0$). For compression or perpendicular-to-grain, $a_{\min} = 2D$ ($C_\Delta = 0.5$) and $a_{	ext{full}} = 4D$ ($C_\Delta = 1.0$).
   - Spacing in a row $s$: $s_{\min} = 3D$ ($C_\Delta = 0.75$) and $s_{	ext{full}} = 4D$ ($C_\Delta = 1.0$).
   - Edge distance & row spacing: Verify compliance with `NDS-2024_Table_12.5.1B_12.5.1C_12.5.1D_12.5.1E.csv` (loaded edge $\ge 4D$; unloaded edge $\ge 1.5D$; outer row distance $\le 5.0	ext{ in.}$ per Sec. 12.5.1.3).
3. **Adjusted Fastener Group Yield Capacity**:
   - **ASD**: $P'_{	ext{yield,ASD}} = N_{	ext{tot}} \cdot Z \cdot C_D \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta$
   - **LRFD**: $P'_{	ext{yield,LRFD}} = N_{	ext{tot}} \cdot Z \cdot 3.32 \cdot 0.65 \cdot \lambda \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta$

### Step 4.3: Brittle Wood Failure Modes in Parallel-to-Grain Tension (NDS Appendix E)
For each connected wood member (both main and side members), compute the adjusted tension design value $F'_t$ and adjusted shear design value $F'_v$ (noting that for glulam in bolted connections, $F'_v$ includes the shear reduction factor $C_{vr} = 0.72$ per [NDS Section 5.3.10 & Appendix E.7](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)):
1. **Net Section Tension Capacity ($Z'_{NT}$, [Eq. E.2-1](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk))**:
   $$Z'_{NT} = F'_t \cdot A_{	ext{net}} = F'_t \cdot t \cdot \left(w - n_{	ext{rows}} \cdot D_hight)$$
2. **Row Tear-Out Capacity ($Z'_{RT}$, [Eq. E.3-2b & E.3-3](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk))**:
   For each row $i$ containing $n_i$ bolts:
   $$s_{	ext{critical},i} = \min\left(	ext{end distance } e_p,\ 	ext{spacing between bolts in row } sight)$$
   $$Z'_{RT,i} = n_i \cdot F'_v \cdot t \cdot s_{	ext{critical},i}, \qquad Z'_{RT} = \sum_{i=1}^{n_{	ext{row}}} Z'_{RT,i}$$
3. **Group Tear-Out Capacity ($Z'_{GT}$, [Eq. E.4-1](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk))** (for $n_{	ext{row}} \ge 2$):
   $$Z'_{GT} = rac{Z'_{RT,1}}{2} + rac{Z'_{RT,n}}{2} + F'_t \cdot A_{	ext{group-net}}$$
   where $A_{	ext{group-net}} = t \cdot \sum_{k=1}^{n_{	ext{row}}-1} \left(s_{	ext{row},k} - D_hight)$ is the net wood tension area between the outermost rows $1$ and $n$.
4. **Governing Connection Capacity ($P'_{	ext{gov}}$)**:
   $$P'_{	ext{gov}} = \min\left(P'_{	ext{yield}},\ Z'_{NT},\ Z'_{RT},\ Z'_{GT}ight)$$

### Step 4.4: Axial Tension & Washer Bearing Verification
When bolts are loaded in axial tension $T_{	ext{bolt}}$ (e.g., knee-brace or post-to-beam through-bolts):
1. **Washer Compression Perpendicular to Grain** ([NDS Section 3.10.2 & Table 3.10.4](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)):
   - Query standard cut washer dimensions $A_{	ext{ID}}, B_{	ext{OD}}$ from `NDS-2024_Table_L1_L7_L8.csv`:
     $$A_{	ext{washer}} = rac{\pi}{4}\left(B_{	ext{OD}}^2 - A_{	ext{ID}}^2ight), \qquad C_b = rac{B_{	ext{OD}} + 0.375}{B_{	ext{OD}}} \quad (	ext{for } B_{	ext{OD}} < 6	ext{ in. and }\ge 3	ext{ in. from end})$$
   - Check bearing capacity:
     $$T_{	ext{bolt}} \le F'_{c\perp} \cdot C_b \cdot A_{	ext{washer}}$$
     *(If standard cut washer is overstressed, specify a custom square steel plate washer of width $b_p 	imes b_p$ and thickness $t_p \ge b_{	ext{cant}} \sqrt{rac{2 f_{	ext{bearing}}}{F_{y,	ext{plate}}}}$).*

## Section 5: Supporting Member / Global Substrate Verification
- **Steel Side Plates / Knife Plates**: Check gross section yielding ($P_n = F_y A_g$), net section rupture ($P_n = F_u A_e$), bolt bearing/tearout ($R_n = 1.2 l_c t F_u \le 2.4 d t F_u$), and block shear rupture per AISC 360-22 Chapter J (Sections J3.10 & J4).
- **Concrete / Masonry Anchor Bolts (`Table 12E`)**: `Table 12E` only governs the **wood dowel/bolt yield limit state** ($Z$). The concrete/CMU substrate must independently be checked for side-face shear breakout, prying, and tension breakout per ACI 318 Chapter 17 / TMS 402.

## Section 6: Mandatory Detailing & Construction Notes
1. **Bolt Hole Tolerance** ([NDS Section 12.1.3.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   - Bolt holes shall be bored a minimum of $D + rac{1}{32}	ext{ in.}$ to a maximum of $D + rac{1}{16}	ext{ in.}$ Forcible driving of bolts is prohibited.
2. **Washer Requirement** ([NDS Section 12.1.3.3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   - A standard cut washer (`Table L8`), malleable iron washer, or metal plate shall be installed between the wood and the bolt head and between the wood and the nut.
3. **Cross-Grain Shrinkage Limit** ([NDS Section 12.5.1.3](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   - The perpendicular-to-grain distance between outermost rows of bolts sharing a single steel splice plate shall not exceed $5.0	ext{ in.}$ unless separate splice plates or vertically slotted holes are provided.

## Section 7: Summary Calculation & Detailing Checklist Table
| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :---: | :--- | :--- | :--- |
| **1** | Bolt Hole & Net Section Area | NDS-2024 Sec. 3.1.2 & Sec. 12.1.3.2 | $D_h = D + 0.0625	ext{ in.}$; $A_{	ext{net}} = t(w - n_{	ext{rows}} D_h)$ |
| **2** | Effective Depth Beam Shear ($d_e$) | NDS-2024 Sec. 3.4.3.3 & Fig. 3E | $f_{v,e} = rac{3V}{2 b d_e} \le F'_v$ |
| **3** | Single/Double Shear Yield Limit ($Z$) | NDS-2024 Sec. 12.3.1, Table 12.3.1A, Tables 12A–12I | $Z = \min(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{II}}, Z_{	ext{III}_m}, Z_{	ext{III}_s}, Z_{	ext{IV}})$ |
| **4** | Adjusted Fastener Group Yield ($n Z'$) | NDS-2024 Table 11.3.1, Sec. 11.3.6, Sec. 12.5.1 | $P'_{	ext{yield}} = N \cdot Z \cdot C_D C_M C_t C_g C_\Delta$ (ASD) |
| **5** | Net Section Tension ($Z'_{NT}$) | NDS-2024 Appendix E, Sec. E.2, Eq. (E.2-1) | $Z'_{NT} = F'_t \cdot A_{	ext{net}}$ |
| **6** | Row Tear-Out Capacity ($Z'_{RT}$) | NDS-2024 Appendix E, Sec. E.3, Eq. (E.3-2b & E.3-3) | $Z'_{RT} = \sum n_i F'_v t \min(e_p, s)$ |
| **7** | Group Tear-Out Capacity ($Z'_{GT}$) | NDS-2024 Appendix E, Sec. E.4, Eq. (E.4-1) | $Z'_{GT} = rac{Z'_{RT,1} + Z'_{RT,n}}{2} + F'_t A_{	ext{group-net}}$ |
| **8** | Washer Bearing Under Bolt Tension | NDS-2024 Sec. 3.10.4 & Appendix Table L8 | $T_{	ext{bolt}} \le F'_{c\perp} C_b A_{	ext{washer}}$ |
