# Calculation Procedure: Open-Frame Trellis & Pergola Wind and Seismic Loads (ASCE 7-22)

## 1. Code References & Database Dependencies
- **Primary Wind Standard**: [ASCE/SEI 7-22 Section 29.4 & Figure 29.4-2 (Open Signs and Single-Plane Open Frames)](https://www.scribd.com/document/512407159/ASCE-7-22-Ch-29-for-PC-sou)
- **Primary Seismic Standard**: [ASCE/SEI 7-22 Chapter 13 (Table 13.5-1 Architectural Appendages)](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html) for wall-ledger attached trellises, or Chapter 12/15 for freestanding structures
- **Load Combinations**: [ASCE/SEI 7-22 Chapter 2 (Sections 2.3 and 2.4)](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)
- **Required CSV Database Tables**:
  - `database/asce_7/v7_22/ASCE7-22_Figure_29.4-2.csv` (Force Coefficients $C_f$ for Open Frames)
  - `database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv` ($K_d = 0.85$)
  - `database/asce_7/v7_22/ASCE7-22_Table_26.10-1.csv` (Exposure Coefficient $K_z$)
  - `database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv` (Nonstructural Seismic Coefficients)
  - `database/asce_7/v7_22/ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv` (LRFD & ASD Load Combinations)

## 2. Input Parameters (`TrellisLoadsInputDTO`)
| Parameter | Symbol | Units | Description / Typical Residential Range |
| :--- | :---: | :---: | :--- |
| Basic Wind Speed | $V$ | mph | Ultimate design wind speed ($95 - 140	ext{ mph}$) |
| Exposure Category | $	ext{Exp}$ | - | Exposure $	ext{B}$, $	ext{C}$, or $	ext{D}$ |
| Trellis Top Height | $z$ | ft | Height from ground to top of trellis purlins/slats (typically $8 - 14	ext{ ft}$) |
| Plan Length & Width | $L_t, B_t$ | ft | Overall plan dimensions of trellis frame |
| Member Cross-Section Type | $	ext{Shape}$ | - | `Flat-Sided` (sawn lumber, glulam, HSS rectangular) or `Rounded` (pipe) |
| Member Depth & Spacing | $d_s, s_s$ | in. | Depth of top lattice slats/rafters and on-center spacing |
| Edge Girder Depth | $d_g$ | in. | Depth of perimeter header/girder beams |
| Post Width & Height | $b_p, H_p$ | in., ft | Width and clear height of supporting columns/posts |
| Number of Parallel Joist Bays | $N_{	ext{frames}}$ | - | Number of exposed parallel vertical planes normal to wind |
| Dead Load (Self-Weight) | $w_D$ | psf | Uniform dead load over plan area $L_t 	imes B_t$ (typically $5 - 12	ext{ psf}$) |
| Attachment Condition | $	ext{Support}$ | - | `Wall_Attached_Ledger` (ledger on house + outer posts) or `Freestanding` (cantilevered posts or knee-braced portal frame) |

## 3. Step-by-Step Calculation Procedure

### Step 1: Velocity Pressure ($q_z$) & Gust Effect Factor ($G$)
1. Lookup $K_z$ at height $z$ (typically $z \le 15	ext{ ft}$) from `ASCE7-22_Table_26.10-1.csv`.
2. Compute velocity pressure $q_z$:
   $$q_z = 0.00256 \cdot K_z \cdot K_{zt} \cdot K_e \cdot V^2 \quad (	ext{psf})$$
3. For rigid open frames (natural frequency $n_1 \ge 1	ext{ Hz}$), take Gust Effect Factor $G = 0.85$ per ASCE 7-22 Section 26.11.

### Step 2: Solidity Ratio ($\epsilon$) & Force Coefficient ($C_f$)
1. Compute the solid-to-gross area ratio $\epsilon$ of the windward elevation plane:
   $$\epsilon = rac{A_s}{A_g}$$
   where $A_s$ is the net projected solid area of edge girders, rafters/slats, knee braces, and upper half of posts, and $A_g$ is the gross framing envelope area.
2. Lookup Force Coefficient $C_f$ from `ASCE7-22_Figure_29.4-2.csv` ([ASCE 7-22 Figure 29.4-2](https://www.scribd.com/document/512407159/ASCE-7-22-Ch-29-for-PC-sou)):
   - For `Flat-Sided` wood or rectangular steel members:
     - $\epsilon < 0.10 \implies C_f = 2.0$
     - $0.10 \le \epsilon \le 0.29 \implies C_f = 1.8$
     - $0.30 \le \epsilon \le 0.70 \implies C_f = 1.6$

### Step 3: Horizontal Wind Force ($F_{W,	ext{horiz}}$) & Vertical Slat Uplift ($F_{W,	ext{vert}}$)
1. **Horizontal Wind Drag on Framing** per [ASCE 7-22 Equation (29.4-1)](https://www.scribd.com/document/512407159/ASCE-7-22-Ch-29-for-PC-sou):
   $$F_{W,	ext{horiz}} = q_z \cdot K_d \cdot G \cdot C_f \cdot A_{f,	ext{eff}} \quad (	ext{lbs})$$
   - Where $A_{f,	ext{eff}}$ accounts for the windward girder plus exposed unshielded portion of sequential interior rafters/slats (conservatively taken as the windward girder area plus $50\%$ of interior parallel rafter projected areas if spacing-to-depth ratio $s_s / d_s \ge 2.0$, plus upper $50\%$ of post projected area).
2. **Vertical Wind Uplift / Downforce on Horizontal Trellis Slats**:
   - Even open pergolas experience vertical aerodynamic uplift on the horizontal top surface of the slats/rafters:
     $$p_{	ext{vert}} = \pm q_z \cdot K_d \cdot G \cdot C_{f,	ext{vert}} \cdot \epsilon_{	ext{plan}} \quad (	ext{psf on gross plan area})$$
     where $\epsilon_{	ext{plan}} = rac{b_{	ext{slat}}}{s_s}$ is the plan solidity ratio of the top slats and $C_{f,	ext{vert}} pprox 1.2 - 1.6$.

### Step 4: Seismic Lateral Force ($F_p$ or Base Shear $V_s$)
1. **Total Seismic Weight ($W_p$)**:
   $$W_p = w_D \cdot L_t \cdot B_t + W_{	ext{posts,trib}} \quad (	ext{lbs})$$
2. **Case A: Wall-Attached Trellis (`Wall_Attached_Ledger`)**:
   - Evaluate as an architectural appendage per [ASCE 7-22 Section 13.3.1 & Table 13.5-1](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html) ($C_{AR} = 2.2$, $R_{po} = 1.5$, $\Omega_{0p} = 1.75$):
     $$F_p = 	ext{clip}\left(0.4 \cdot S_{DS} \cdot I_p \cdot W_p \cdot rac{H_f}{R_\mu} \cdot rac{C_{AR}}{R_{po}},\ 0.3 S_{DS} I_p W_p,\ 1.6 S_{DS} I_p W_pight)$$
3. **Case B: Freestanding Cantilevered Post or Knee-Braced Trellis (`Freestanding`)**:
   - Evaluate using nonbuilding structure coefficients (ASCE 7-22 Table 15.4-2: Cantilevered column systems $R = 1.25 - 1.5, \Omega_0 = 1.5 - 2.0$, or ordinary moment frame $R = 3.5$):
     $$V_{	ext{seismic}} = C_s \cdot W_p = \left(rac{S_{DS}}{R / I_e}ight) \cdot W_p$$

### Step 5: Member & Post Base Reactions (LRFD & ASD)
1. **Cantilevered Post Base Reactions** (for $N_p$ posts resisting lateral load $H_{	ext{tot}} = \max(0.6 F_{W,	ext{horiz}}, 0.7 F_p)$ in ASD):
   - Shear per Post: $V_{	ext{post}} = rac{H_{	ext{tot}}}{N_p}$
   - Overturning Moment at Post Base: $M_{	ext{base}} = V_{	ext{post}} \cdot H_p$
2. **Knee-Braced Frame Reactions** (knee brace at vertical drop $a_k$ below beam on post):
   - Brace Axial Force: $P_{	ext{brace}} = rac{V_{	ext{post}} \cdot H_p}{a_k \cdot \sin	heta_k}$
   - Maximum Post Bending Moment (at knee brace attachment): $M_{	ext{post}} = V_{	ext{post}} \cdot (H_p - a_k)$

## 4. Output DTO (`TrellisLoadsOutputDTO`) & Downstream Routing
- `qz_psf`: Velocity pressure at trellis height $z$ ($	ext{psf}$)
- `epsilon_elev`, `epsilon_plan`: Elevation and plan solidity ratios
- `Cf`: Open-frame force coefficient from `Figure 29.4-2`
- `Fw_horiz_lbs`, `Fw_vert_lbs`: Total unfactored horizontal and vertical wind forces ($	ext{lbs}$)
- `Fp_seismic_lbs`: Total horizontal seismic force ($	ext{lbs}$)
- `V_post_ASD`, `M_base_ASD`, `P_uplift_ASD`, `P_down_ASD`: Governing ASD post reactions
- **Downstream Connection Modules**:
  - Wood post-to-beam & knee-brace bolted/screwed connection $ightarrow$ `nds/wood_bolt_dowel_calc.py`
  - Embedded steel column in concrete/CMU or post base plate $ightarrow$ `aci318/concrete_anchor_bolt_calc.py`

## 5. Reference Verification Example
- **Input**: Freestanding wood pergola $12	ext{ ft} 	imes 16	ext{ ft}$ plan, height $z = H_p = 10	ext{ ft}$ on $N_p = 4$ cantilevered posts ($6	imes 6$), Exposure C, $V = 115	ext{ mph}$, $w_D = 8	ext{ psf}$, $S_{DS} = 1.0g$. Projected flat-sided member area normal to wind $A_{f,	ext{eff}} = 28.0	ext{ ft}^2$ ($\epsilon = 0.18$).
- **Calculation**:
  1. At $z = 10	ext{ ft}$ (Exp C), $K_z = 0.85 \implies q_z = 0.00256 	imes 0.85 	imes 115^2 = 28.78	ext{ psf}$.
  2. From `ASCE7-22_Figure_29.4-2.csv` at $\epsilon = 0.18$ (`0.1 to 0.29`), $C_f = 1.8$.
  3. Horizontal Wind Force: $F_{W,	ext{horiz}} = 28.78 	imes 0.85 	imes 0.85 	imes 1.8 	imes 28.0 = 1,048	ext{ lbs}$.
  4. **ASD Post Base Demand** ($0.6W$): $V_{	ext{post,ASD}} = 0.6 	imes 1,048 / 4 = 157.2	ext{ lbs/post}$; $M_{	ext{base,ASD}} = 157.2 	imes 10.0	ext{ ft} = 1,572	ext{ lb-ft/post}$.
