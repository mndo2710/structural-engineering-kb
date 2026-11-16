# Calculation Procedure: Lag Screw & Structural Screw (Simpson SDS/SDWS) Connections (ANSI/AWC NDS 2024)

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Connection Types Covered**:
  1. **Wood-to-Wood Single Shear**: Wood side member of thickness $t_s = \ell_s$ attached to a wood main member of thickness $t_m$ using standard hex lag screws ([ANSI/ASME B18.2.1](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)) or proprietary high-strength structural wood screws ([Simpson Strong-Tie Strong-Drive SDS per ICC-ES ESR-2236](https://icc-es.org/wp-content/uploads/report-directory/ESR-2236.pdf) and [SDWS Timber Screws per IAPMO UES ER-192](https://www.scribd.com/document/433914075/er-0192)).
  2. **Steel-to-Wood Single Shear**: ASTM A36 ($t_s \ge 1/4	ext{ in.}$) or ASTM A653 Grade 33/45 cold-formed steel side plate ($16	ext{ ga}$ to $3	ext{ ga}$) attached to a wood main member (such as ledger brackets, holdown straps, beam hangers, or guardrail post base plates).
- **Governing Codes & Standards**:
  - [ANSI/AWC NDS-2024 Chapter 2 (Design Values for Structural Members)](https://drive.google.com/file/d/1x61PCqaWFKYZjX-zAoh9hQIKQuRlmqd6/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Chapter 11 (Mechanical Connections)](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Chapter 12 (Dowel-Type Fasteners)](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)
  - [ANSI/AWC NDS-2024 Appendix E (Local Stresses in Fastener Groups), Appendix I (Yield Limit Equations), Appendix L (Table L2), and Appendix N (LRFD)](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)
  - [ICC-ES Evaluation Report ESR-2236 (Simpson Strong-Drive SDS Heavy-Duty Connector Screws)](https://icc-es.org/wp-content/uploads/report-directory/ESR-2236.pdf)
- **Required CSV Database Tables**:
  - `database/nds_wood/v2024/NDS-2024_Table_11.3.1.csv` (Applicability of Adjustment Factors)
  - `database/nds_wood/v2024/NDS-2024_Table_11.3.3.csv` & `NDS-2024_Table_11.3.4.csv` ($C_M, C_t$)
  - `database/nds_wood/v2024/NDS-2024_Table_11.3.6A.csv` & `NDS-2024_Table_11.3.6C.csv` ($C_g$)
  - `database/nds_wood/v2024/NDS-2024_Table_12.2A.csv` (Lag Screw Reference Withdrawal $W$)
  - `database/nds_wood/v2024/NDS-2024_Table_12.3.3.csv` & `NDS-2024_Table_12.3.3A.csv` ($F_e, G$)
  - `database/nds_wood/v2024/NDS-2024_Table_12.5.1A.csv` & `NDS-2024_Table_12.5.1B_12.5.1C_12.5.1D_12.5.1E.csv` ($C_\Delta$ Geometry)
  - `database/nds_wood/v2024/NDS-2024_Table_12J.csv` (Lag Screw Wood-to-Wood $Z$) & `NDS-2024_Table_12K.csv` (Lag Screw Steel-to-Wood $Z$)
  - `database/nds_wood/v2024/NDS-2024_Table_L2_L3_L4_I1.csv` (Dimensions $D, D_r, T, E, F_{yb}$)
  - `database/manufacturer_catalogs/simpson_strong_tie/ICC-ESR-2236_Table_1_2_3_4_5.csv` (Simpson SDS Capacities)

### 1.2 Load Path & Force Transfer Mechanism
1. **Direct Shear Force ($V_\parallel, V_\perp$)**: Transferred across the shear interface via dowel bearing stress ($F_{es}, F_{em}$) in the side and main members coupled with flexural hinge formation ($F_{yb}$) in the fastener shank/root (European Yield Model Modes $	ext{I}_m, 	ext{I}_s, 	ext{II}, 	ext{III}_m, 	ext{III}_s, 	ext{IV}$).
2. **Axial Tension / Out-of-Plane Pullout ($T$)**: Transferred via shear along the embedded thread cylinder in the main member ($W' \cdot p_t$), reacted by bearing under the hex washer head / pull-through resistance ($W'_H$) of the side member, and limited by the net tensile rupture strength of the steel screw root ($N_a$ or $N_u$).
3. **Combined Lateral & Withdrawal ($V + T$)**: Resolved at the resultant load angle $lpha = rctan(T / V)$ relative to the wood surface using the interaction equation $Z'_lpha$ ([NDS Section 12.4.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).

## Section 2: Load Combinations & Internal Forces at the Critical Section
- **Governing Load Combinations**: Evaluate both ASD ([ASCE 7-22 Section 2.4](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)) and LRFD ([ASCE 7-22 Section 2.3](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html) & [NDS Appendix N](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)) from `ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv`.
- **Fastener Group Force Distribution** (for $n_{	ext{rows}}$ rows of $n_f$ fasteners per row, total $N_{	ext{tot}} = n_{	ext{rows}} \cdot n_f$, subjected to axial force $P$, in-plane shear $V$,in-plane eccentricity $e_{ip}$, and out-of-plane overturning moment $M_{	ext{oop}}$):
  - **Direct Shear per Fastener**:
    $$v_x = rac{V_x}{N_{	ext{tot}}}, \qquad v_y = rac{V_y}{N_{	ext{tot}}}$$
  - **Torsional Shear from In-Plane Eccentricity ($M_{	ext{ip}} = V \cdot e_{	ext{ip}}$)**:
    $$v_{	ext{tor},i} = rac{M_{	ext{ip}} \cdot r_i}{\sum_{j=1}^{N_{	ext{tot}}} (x_j^2 + y_j^2)}$$
  - **Maximum Tension per Fastener from Direct Pullout ($T_{	ext{tot}}$) + Out-of-Plane Moment ($M_{	ext{oop}}$)** (with compression lever arm $d_e$):
    $$t_{\max} = rac{T_{	ext{tot}}}{N_{	ext{tot}}} + rac{M_{	ext{oop}}}{n_{	ext{tension}} \cdot d_e}$$

## Section 3: Primary Member Verification
- **Net Cross-Sectional Area ($A_{	ext{net}}$)** ([NDS Section 3.1.2](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)):
  - Deduct the projected hole area of all lag screws occurring at the critical plane (staggered lag screws spaced $< 4D$ parallel to grain are treated as occurring at the same critical section per [NDS Section 3.1.2.2](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)):
    $$A_{	ext{net}} = A_{	ext{gross}} - n_{	ext{rows}} \cdot d_{	ext{hole}} \cdot t_{	ext{member}}$$
- **Reduced Design Depth at Eccentric Connections ($d_e$)**:
  - Where lag screws induce perpendicular-to-grain shear in a bending member ([NDS Section 3.4.3.3](https://drive.google.com/file/d/17QBgQR4YSN5_utj1eukebEPjsVAoEmQ6/view?usp=drivesdk)), check adjusted shear stress using effective depth $d_e$:
    $$f_{v,e} = rac{3 V}{2 b d_e} \le F'_v \quad 	ext{where } d_e 	ext{ is distance from unloaded edge to furthest fastener}$$

## Section 4: Sequential Connection / Limit State Checks Along the Load Path

### Step 4.1: Fastener Geometry, Penetration ($p$), and Penetration Depth Factor ($C_d$)
1. **Standard Hex Lag Screws** ([NDS Section 12.1.4 & Appendix Table L2](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)):
   - Lookup nominal diameter $D$, root diameter $D_r$, minimum thread length $T$, tapered tip length $E$, and bending yield strength $F_{yb}$ from `NDS-2024_Table_L2_L3_L4_I1.csv`.
   - Total penetration into main member (including tip): $p_{	ext{tot}} = L - t_s$.
   - **Effective Penetration for Lateral Load ($p$)**:
     $$p = L - t_s - E \ge p_{\min} = 4D$$
     *(If $p < 4D$, the lateral capacity $Z = 0$ per [NDS Section 12.1.4.6](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).*
   - **Penetration Depth Factor ($C_d$)** for tabulated values in `Table 12J` / `Table 12K` (which assume $p = 8D$):
     $$C_d = \min\left(1.0,\ rac{p}{8D}ight) \quad 	ext{for } 4D \le p < 8D$$
   - **Effective Thread Length for Withdrawal ($p_t$)**:
     $$p_t = \min\left(T - E,\ L - t_s - Eight)$$
2. **Simpson Strong-Drive SDS Screws** ([ICC-ES ESR-2236 Sections 3.2, 4.1.5, 4.1.6](https://icc-es.org/wp-content/uploads/report-directory/ESR-2236.pdf)):
   - Query `ICC-ESR-2236_Table_1_2_3_4_5.csv`: $D = 0.256	ext{ in.}$, $D_r = 0.188	ext{ in.}$, $D_s = 0.239	ext{ in.}$, $L_{	ext{tip}} = 0.334	ext{ in.}$, $F_{yb,	ext{spec}} = 172,000	ext{ psi}$ (Carbon) or $164,000	ext{ psi}$ (SS).
   - Main member dowel bearing length for NDS yield equations: $\ell_m = (L - t_s) - 0.5 L_{	ext{tip}}$.

### Step 4.2: Reference Lateral Design Value ($Z$) — Yield Limit Equations (NDS Table 12.3.1A)
Compute dowel bearing strengths $F_{em}(	heta_m)$ and $F_{es}(	heta_s)$ from `NDS-2024_Table_12.3.3.csv` (using Hankinson's formula $F_{e	heta} = rac{F_{e\parallel} F_{e\perp}}{F_{e\parallel}\sin^2	heta + F_{e\perp}\cos^2	heta}$ at load-to-grain angle $	heta$, or $F_{es} = 61,850	ext{ psi}$ for ASTM A653 Gr. 33 steel / $87,000	ext{ psi}$ for ASTM A36 steel / $1.375 F_u$ per ESR-2236).
Using $D_{	ext{calc}} = D_r$ (for reduced-body lag screws or threaded portion at shear plane per [NDS Appendix I.5](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)), $\ell_m = p$, $\ell_s = t_s$, $R_e = F_{em}/F_{es}$, $R_t = \ell_m/\ell_s$, and reduction term $R_d$ from [NDS Table 12.3.1B](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk) ($K_	heta = 1 + 0.25(	heta/90)$):
$$egin{aligned}
Z_{	ext{I}_m} &= rac{D_{	ext{calc}} \ell_m F_{em}}{R_d} \quad (	ext{Eq. 12.3-1}) \
Z_{	ext{I}_s} &= rac{D_{	ext{calc}} \ell_s F_{es}}{R_d} \quad (	ext{Eq. 12.3-2}) \
Z_{	ext{II}} &= rac{k_1 D_{	ext{calc}} \ell_s F_{es}}{R_d} \quad (	ext{Eq. 12.3-3}) \
Z_{	ext{III}_m} &= rac{k_2 D_{	ext{calc}} \ell_m F_{em}}{(1 + 2R_e) R_d} \quad (	ext{Eq. 12.3-4}) \
Z_{	ext{III}_s} &= rac{k_3 D_{	ext{calc}} \ell_s F_{em}}{(2 + R_e) R_d} \quad (	ext{Eq. 12.3-5}) \
Z_{	ext{IV}} &= rac{D_{	ext{calc}}^2}{R_d} \sqrt{rac{2 F_{em} F_{yb}}{3(1 + R_e)}} \quad (	ext{Eq. 12.3-6})
\end{aligned}$$
where:
$$k_1 = rac{\sqrt{R_e + 2R_e^2(1 + R_t + R_t^2) + R_t^2 R_e^3} - R_e(1 + R_t)}{1 + R_e}$$
$$k_2 = -1 + \sqrt{2(1 + R_e) + rac{2 F_{yb}(1 + 2R_e) D_{	ext{calc}}^2}{3 F_{em} \ell_m^2}}, \qquad k_3 = -1 + \sqrt{rac{2(1 + R_e)}{R_e} + rac{2 F_{yb}(2 + R_e) D_{	ext{calc}}^2}{3 F_{em} \ell_s^2}}$$
The reference lateral design value is $Z = \min\left(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{II}}, Z_{	ext{III}_m}, Z_{	ext{III}_s}, Z_{	ext{IV}}ight)$ (or lookup directly from `NDS-2024_Table_12J.csv`, `NDS-2024_Table_12K.csv`, or `ICC-ESR-2236_Table_1_2_3_4_5.csv`).

### Step 4.3: Adjustment Factors ($C_D, C_M, C_t, C_g, C_\Delta, C_{eg}$) & Adjusted Lateral Capacity ($Z'$)
Per [NDS Table 11.3.1](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk) (`NDS-2024_Table_11.3.1.csv`):
- **ASD Adjusted Lateral Design Value**:
  $$Z'_{	ext{ASD}} = Z \cdot C_D \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta \cdot C_{eg}$$
- **LRFD Factored Lateral Resistance** ($K_F = 3.32$, $\phi_z = 0.65$, $\lambda$ from `Table N3`):
  $$Z'_{	ext{LRFD}} = Z \cdot K_F \cdot \phi_z \cdot \lambda \cdot C_M \cdot C_t \cdot C_g \cdot C_\Delta \cdot C_{eg}$$
- **Group Action Factor ($C_g$)** ([NDS Section 11.3.6.1 Eq. 11.3-1](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)):
  - For $D < 1/4	ext{ in.}$, $C_g = 1.0$. For $D \ge 1/4	ext{ in.}$, compute via algebraic equation Eq. 11.3-1 using load/slip modulus $\gamma = 180,000 D^{1.5}$ (wood-to-wood) or $\gamma = 270,000 D^{1.5}$ (metal-to-wood), or interpolate from `NDS-2024_Table_11.3.6A.csv` / `11.3.6C.csv`.
- **Geometry Factor ($C_\Delta$)** ([NDS Section 12.5.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
  - Query `NDS-2024_Table_12.5.1A.csv` and `NDS-2024_Table_12.5.1B_12.5.1C_12.5.1D_12.5.1E.csv`:
    $$C_\Delta = \min\left(1.0,\ rac{a_{	ext{actual}}}{a_{\min, C_\Delta=1.0}},\ rac{s_{	ext{actual}}}{s_{\min, C_\Delta=1.0}}ight) \ge 0.50$$
- **End-Grain Factor ($C_{eg}$)** ([NDS Section 12.5.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)): $C_{eg} = 0.67$ if lag screw is inserted into end grain parallel to wood fibers; $1.00$ in side grain.

### Step 4.4: Withdrawal ($W'$) & Combined Lateral + Withdrawal ($Z'_lpha$)
1. **Reference Withdrawal Value ($W$, $	ext{lbs/in.}$)**:
   - Lookup from `NDS-2024_Table_12.2A.csv` ($W = 1800 G^{3/2} D^{3/4}$ per [NDS Section 12.2.1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)), or $W = 172	ext{ lbf/in.}$ for Simpson SDS in DF-L ($G=0.50$) per `ICC-ESR-2236_Table_1_2_3_4_5.csv`.
2. **Adjusted Withdrawal Capacity ($W'_{	ext{tot}}$)**:
   - **ASD**: $W'_{	ext{tot,ASD}} = (W \cdot p_t) \cdot C_D \cdot C_M \cdot C_t \cdot C_{eg}$ (where $C_{eg} = 0.75$ for lag screws in end grain per NDS Sec. 12.5.2; $1.0$ in side grain).
   - **LRFD**: $W'_{	ext{tot,LRFD}} = (W \cdot p_t) \cdot 3.32 \cdot 0.65 \cdot \lambda \cdot C_M \cdot C_t \cdot C_{eg}$.
   - **Upper Bound Checks**: Verify $W'_{	ext{tot}} \le W'_H$ (Head Pull-Through per [NDS Table 12.2F](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)) and $W'_{	ext{tot}} \le N_{	ext{steel}}$ ($N_a = 1,430	ext{ lbs}$ ASD or $N_u = 2,145	ext{ lbs}$ LRFD for SDS per [ESR-2236 Table 1](https://icc-es.org/wp-content/uploads/report-directory/ESR-2236.pdf), without $C_D$ increase on steel strength).
3. **Combined Lateral and Withdrawal Interaction ($Z'_lpha$)** ([NDS Section 12.4.1 Eq. 12.4-1](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   When resultant load $R_{	ext{req}} = \sqrt{V_{	ext{req}}^2 + T_{	ext{req}}^2}$ acts at angle $lpha = rctan(T_{	ext{req}} / V_{	ext{req}})$ to the wood surface:
   $$Z'_lpha = rac{(W' \cdot p_t) \cdot Z'}{(W' \cdot p_t) \cos^2lpha + Z' \sin^2lpha} \ge R_{	ext{req}}$$

### Step 4.5: Brittle Wood Failure Modes — Net Tension, Row Tear-Out & Group Tear-Out (NDS Appendix E)
For multiple-fastener connections loaded parallel to grain in tension ([NDS Section 11.1.2 & Appendix E](https://drive.google.com/file/d/1PBnAKQaza1C-JolltIPmreOAAQGNJIc6/view?usp=drivesdk)):
1. **Net Section Tension Capacity ($Z'_{nt}$, Eq. E.2-1)**:
   $$Z'_{nt} = F'_t \cdot A_{	ext{net}}$$
2. **Row Tear-Out Capacity ($Z'_{rt}$, Eq. E.3-1 & E.3-2)**:
   $$Z'_{rt,i} = n_i \cdot F'_v \cdot t \cdot s_{	ext{critical}}, \qquad Z'_{rt} = \sum_{i=1}^{n_{	ext{rows}}} Z'_{rt,i}$$
   where $s_{	ext{critical}} = \min(	ext{end distance } a,\ 	ext{spacing in row } s)$.
3. **Group Tear-Out Capacity ($Z'_{gt}$, Eq. E.4-1)**:
   $$Z'_{gt} = rac{Z'_{rt,1}}{2} + rac{Z'_{rt,n}}{2} + F'_t \cdot A_{	ext{group-net}}$$
   where $A_{	ext{group-net}}$ is the net cross-sectional area between the outer rows of fasteners.

## Section 5: Supporting Member / Global Substrate Verification
- **Cross-Grain Tension Avoidance** ([NDS Section 11.1.3](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)): Never rely on unreinforced wood in cross-grain bending or tension perpendicular to grain (e.g., guardrail post bolted only to rim joist without tension tie to floor joist).
- **Steel Side Plate Checks**: When connecting via steel side plate or bracket, verify steel plate gross shear yielding, net shear rupture, bolt hole bearing/tearout, and block shear per AISC 360 Chapter J (without applying wood load duration factor $C_D$ per [NDS Section 11.2.3](https://drive.google.com/file/d/1ByJGm0astZ_xwDT5Wbd5wUWFN2s-8al3/view?usp=drivesdk)).

## Section 6: Mandatory Detailing & Construction Notes
1. **Lead Hole Boring for Standard Lag Screws** ([NDS Section 12.1.4.2](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)):
   - Clearance hole for unthreaded shank: diameter $= D$, depth $=$ length of unthreaded shank $S$.
   - Lead hole for threaded portion: diameter $= 65\% - 85\% D$ (for $G > 0.60$), $60\% - 75\% D$ (for $0.50 < G \le 0.60$, e.g. Southern Pine), and $40\% - 70\% D$ (for $G \le 0.50$, e.g. Douglas Fir-Larch and SPF).
   - Lag screws shall be turned into lead holes with a wrench, never driven with a hammer; soap or lubricant may be used on threads ([NDS Section 12.1.4.4](https://drive.google.com/file/d/1uSfqqSxMmM9FXBSB0eI2rDcGnhIjslgE/view?usp=drivesdk)).
2. **Self-Drilling Installation for Simpson SDS Screws** ([ICC-ES ESR-2236 Section 4.3](https://icc-es.org/wp-content/uploads/report-directory/ESR-2236.pdf)):
   - Install using a $3/8	ext{ in.}$ hex driver and low-speed drill without predrilling; observe minimum end, edge, and row spacing per `Table 4A` (for tested values) or `Table 4B` (for NDS values).
3. **Corrosion Protection**: Use hot-dip galvanized (ASTM A153), Double-Barrier Coating (ESR-2236 Exposure Condition 3), or Type 316 Stainless Steel fasteners in exterior or preservative-treated wood applications.

## Section 7: Summary Calculation & Detailing Checklist Table
| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :---: | :--- | :--- | :--- |
| **1** | Effective Penetration Check | NDS-2024 Sec. 12.1.4.6 & Table L2 | $p = L - t_s - E \ge 4D$; $C_d = \min(1.0, p / 8D)$ |
| **2** | Single Fastener Yield Limit ($Z$) | NDS-2024 Sec. 12.3.1, Table 12.3.1A, 12J, 12K | $Z = \min(Z_{	ext{I}_m}, Z_{	ext{I}_s}, Z_{	ext{II}}, Z_{	ext{III}_m}, Z_{	ext{III}_s}, Z_{	ext{IV}})$ |
| **3** | Adjusted Lateral Capacity ($Z'$) | NDS-2024 Table 11.3.1, Sec. 11.3.6, Sec. 12.5.1 | $V_{	ext{req}} \le n \cdot Z \cdot C_D C_M C_t C_g C_\Delta C_{eg}$ (ASD) |
| **4** | Adjusted Withdrawal Capacity ($W'$) | NDS-2024 Sec. 12.2.1, Table 12.2A, Table 12.2F | $T_{	ext{req}} \le n \cdot \min(W' p_t,\ W'_H,\ N_{	ext{steel}})$ |
| **5** | Combined Lateral & Withdrawal ($Z'_lpha$) | NDS-2024 Sec. 12.4.1, Eq. (12.4-1) | $R_{	ext{req}} \le rac{(W' p_t) Z'}{(W' p_t)\cos^2lpha + Z'\sin^2lpha}$ |
| **6** | Wood Group Tear-Out & Net Section | NDS-2024 Sec. 11.1.2 & Appendix E (Eq. E.2-1 to E.4-1) | $P_{	ext{req}} \le \min(Z'_{nt},\ Z'_{rt},\ Z'_{gt})$ |
| **7** | Effective Depth Beam Shear ($d_e$) | NDS-2024 Sec. 3.4.3.3 | $f_{v,e} = rac{3V}{2 b d_e} \le F'_v$ |
