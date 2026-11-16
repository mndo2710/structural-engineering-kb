# Calculation Procedure: Attached Awning & Canopy Wind and Seismic Loads (ASCE 7-22)

## 1. Code References & Database Dependencies

* **Primary Wind Standard**: [ASCE/SEI 7-22 Section 30.11 (Attached Canopies on Buildings with \$h \\le 60	ext{ ft}$)](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784414248/part/provisions/standard-chapter/s30/standard-sec-ver/s30.11.ver.atom) and [ASCE 7 Canopy Wind Pressure Provisions](https://www.google.com/search?q=https%3A%2F%2Fstudylib.net%2Fdoc%2F27010719%2Fwind-load-on-a-canopy-asce16)

* **Primary Seismic Standard**: [ASCE/SEI 7-22 Chapter 13 (Seismic Design Requirements for Nonstructural Components, Section 13.3.1 & Table 13.5-1)](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html)

* **Load Combinations**: [ASCE/SEI 7-22 Chapter 2 (Sections 2.3.1, 2.3.6, 2.4.1, and 2.4.5)](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)

* **Required CSV Database Tables**:

  * `database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv` (Wind Directionality Factor $K_d = 0.85$)

  * `database/asce_7/v7_22/ASCE7-22_Table_26.9-1.csv` (Ground Elevation Factor $K_e$)

  * `database/asce_7/v7_22/ASCE7-22_Table_26.10-1.csv` (Velocity Pressure Exposure Coefficient $K_h$)

  * `database/asce_7/v7_22/ASCE7-22_Figure_30.11-1A_1B.csv` (Attached Canopy $(GC_p)$ Coefficients)

  * `database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv` (Architectural Component Seismic Coefficients $C_{AR}, R_{po}, \Omega_{0p}$)

  * `database/asce_7/v7_22/ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv` (LRFD & ASD Load Combinations)

## 2. Input Parameters (`AwningCanopyInputDTO`)

| Parameter | Symbol | Units | Description / Typical Residential Range | 
| ----- | ----- | ----- | ----- | 
| Basic Wind Speed | $V$ | mph | Ultimate design wind speed per Risk Category (e.g., $95 - 140	ext{ mph}$) | 
| Exposure Category | $ext{Exp}$ | \- | Exposure $ext{B}$, $ext{C}$, or $ext{D}$ | 
| Topographic Factor | $K_{zt}$ | \- | Default $1.00$ unless on hill/escarpment | 
| Site Elevation | $z_e$ | ft | Ground elevation above sea level for $K_e$ lookup | 
| Main Building Mean Roof Height | $h$ | ft | Mean roof height of supporting building ($h \le 60	ext{ ft}$) | 
| Building Eave Height | $h_e$ | ft | Eave height of supporting wall (equals $h$ for flat roof) | 
| Canopy Height Above Ground | $h_c$ | ft | Vertical height from grade to attached canopy ($h_c < 0.90 h_e$) | 
| Canopy Projection Width | $B_c$ | ft | Horizontal cantilever projection from exterior wall face | 
| Bracket / Outlooker Spacing | $S_b$ | ft | On-center spacing of supporting cantilever beams or brackets | 
| Canopy Tributary Length | $L_c$ | ft | Member span length (e.g., $B_c$ for cantilever beam or $S_b$ for decking) | 
| Canopy Slope | $heta$ | deg | Roof pitch of canopy ($heta \le 10^\circ$ for Section 30.11 applicability) | 
| Canopy Dead Load | $w_D$ | psf | Self-weight of framing, decking, and fascia (typically $8 - 20	ext{ psf}$) | 
| Canopy Roof Live Load | $w_{Lr}$ | psf | $20	ext{ psf}$ (or $10	ext{ psf}$ for fabric awnings per IBC Sec. 1607.14.2.4) | 
| Design Spectral Acceleration | $S_{DS}$ | $g$ | Short-period spectral response acceleration parameter | 
| Component Importance Factor | $I_p$ | \- | Typically $1.0$ (or $1.5$ for egress/life-safety canopies) | 
| Supporting Structure SFRS Factor | $R, \Omega_0, I_e$ | \- | Main building seismic factors (e.g., Light-frame wood shear wall $R = 6.5, \Omega_0 = 3.0, I_e = 1.0$) | 
| Support Configuration | $ext{Type}$ | \- | `Cantilever_Bracket` (moment connection at wall) or `TieBack_Hanger` (pinned ledger + diagonal tension rod at vertical drop $H_{rod}$ and horizontal offset $L_{rod}$) | 

## 3. Step-by-Step Calculation Procedure

### Step 1: Geometric Applicability & Effective Wind Area ($A$)

1. Verify [ASCE 7-22 Section 30.11](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784414248/part/provisions/standard-chapter/s30/standard-sec-ver/s30.11.ver.atom) limits:
   

   $$
   h \le 60	ext{ ft}, \quad rac{h_c}{h_e} < 0.90, \quad 	heta \le 10^\circ
   $$

   
   *(If* $h_c / h_e \ge 0.90$*, treat the canopy as a roof overhang per `cc_wind_overhang_workflow.md`).*

2. Compute the height ratio:
   

   $$
   r_h = rac{h_c}{h_e}
   $$

3. Compute the Effective Wind Area $A$ for the component under consideration:

   * **Sheathing / Decking Fasteners**: $A_{	ext{deck}} = \max\left(S_b \cdot 1.0	ext{ ft},\ rac{S_b^2}{3} ight)$

   * **Cantilever Bracket / Outlooker Beam / Wall Connection**:
     

     $$
     A_{	ext{frame}} = \max\left(B_c \cdot S_b,\ rac{B_c^2}{3} ight)
     $$

### Step 2: Velocity Pressure at Mean Roof Height ($q_h$)

1. Retrieve $K_h$ at $z = h$ from `ASCE7-22_Table_26.10-1.csv`, $K_d = 0.85$ from `ASCE7-22_Table_26.6-1.csv`, and $K_e$ from `ASCE7-22_Table_26.9-1.csv`.

2. Compute velocity pressure $q_h$ per [ASCE 7-22 Equation (26.10-1)](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784414248/part/provisions/standard-chapter/s30/standard-sec-ver/s30.11.ver.atom):
   

   $$
   q_h = 0.00256 \cdot K_h \cdot K_{zt} \cdot K_e \cdot V^2 \quad (	ext{psf})
   $$

### Step 3: Surface & Net Canopy Wind Pressures ($p$)

Per [ASCE 7-22 Equation (30.11-1)](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784414248/part/provisions/standard-chapter/s30/standard-sec-ver/s30.11.ver.atom) and [ASCE 7 Section 30.11 Canopy Provisions](https://www.google.com/search?q=https%3A%2F%2Fstudylib.net%2Fdoc%2F27010719%2Fwind-load-on-a-canopy-asce16):

$$
p = q_h \cdot K_d \cdot (GC_p) \quad (	ext{psf})
$$

1. **Individual Surface Elements (`Figure 30.11-1A`)**:

   * Query `ASCE7-22_Figure_30.11-1A_1B.csv` at $r_h = h_c / h_e$ and $A = A_{	ext{deck}}$:

     * Upper surface positive downward pressure $p_{	ext{upper},+}$ and upward suction $p_{	ext{upper},-}$

     * Lower surface (soffit) upward pressure $p_{	ext{lower},+}$ and downward suction $p_{	ext{lower},-}$

2. **Primary Canopy Framing & Wall Connections (`Figure 30.11-1B`)**:

   * Query `ASCE7-22_Figure_30.11-1B` net pressure coefficients at $r_h = h_c / h_e$ and $A = A_{	ext{frame}}$:

     * Net Downward Wind Pressure:
       

       $$
       p_{	ext{net},+} = q_h \cdot K_d \cdot (GC_p)_{	ext{net},+} \quad (	ext{psf})
       $$

     * Net Upward (Uplift) Wind Pressure:
       

       $$
       p_{	ext{net},-} = q_h \cdot K_d \cdot (GC_p)_{	ext{net},-} \quad (	ext{psf})
       $$

3. **Horizontal Fascia Wind Drag (**$F_{	ext{fascia}}$**)**:

   * For a vertical fascia board of depth $d_f$ ($ext{ft}$) at the leading edge of the canopy, compute horizontal wind pressure $p_{	ext{fascia}} = q_h \cdot K_d \cdot (GC_p)_{	ext{wall}}$ (typically $(GC_p) = \pm 1.3$ for small fascia effective wind area).

### Step 4: Nonstructural Seismic Force ($F_p$) per ASCE 7-22 Chapter 13

1. Query `ASCE7-22_Table_13.5-1.csv` under **"Appendages and Ornamentations"** ([ASCE 7-22 Table 13.5-1](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html)):

   * $C_{AR} = 2.2$ (supported above grade plane by a structure) or $1.8$ (at/below grade)

   * $R_{po} = 1.5$

   * $\Omega_{0p} = 1.75$ (for concrete/masonry anchorage checks)

2. Compute height amplification factor $H_f$ at attachment height $z = h_c$ per [ASCE 7-22 Equation (13.3-5)](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html):
   

   $$
   H_f = 1.0 + 2.5 \cdot \left(rac{h_c}{h} ight)
   $$

3. Compute structure ductility reduction factor $R_\mu$ per [ASCE 7-22 Equation (13.3-6)](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html):
   

   $$
   R_\mu = \max\left(1.3,\ \sqrt{rac{1.1 \cdot R}{I_e \cdot \Omega_0}} ight)
   $$

4. Compute horizontal seismic force $F_p$ per tributary bracket weight $W_p = w_D \cdot B_c \cdot S_b$ per [ASCE 7-22 Equations (13.3-1) through (13.3-3)](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html):
   

   $$
   F_{p,	ext{calc}} = 0.4 \cdot S_{DS} \cdot I_p \cdot W_p \cdot \left(rac{H_f}{R_\mu} ight) \cdot \left(rac{C_{AR}}{R_{po}} ight)
   $$

   $$
   F_{p,\min} = 0.3 \cdot S_{DS} \cdot I_p \cdot W_p, \quad F_{p,\max} = 1.6 \cdot S_{DS} \cdot I_p \cdot W_p
   $$

   $$
   F_p = \min\left(\max(F_{p,	ext{calc}}, F_{p,\min}), F_{p,\max} ight)
   $$

5. Vertical seismic force effect ([ASCE 7-22 Section 13.3.1.2](https://pdfcoffee.com/asce-7-22-ch-13-for-pc-3-pdf-free.html)):
   

   $$
   E_v = \pm 0.2 \cdot S_{DS} \cdot W_p
   $$

### Step 5: Wall Connection Forces & LRFD / ASD Load Combinations

For each bracket spaced at $S_b$:

1. **Unfactored Line Loads Along Projection** $B_c$ ($ext{plf}$):

   * Dead: $q_D = w_D \cdot S_b$

   * Roof Live: $q_{Lr} = w_{Lr} \cdot S_b$

   * Wind Downward: $q_{W,+} = p_{	ext{net},+} \cdot S_b$

   * Wind Uplift: $q_{W,-} = p_{	ext{net},-} \cdot S_b$ (upward)

2. **Support Reactions by Structural Configuration**:

   * **Case A: Pure Cantilever Bracket (`Cantilever_Bracket`)**:

     * Vertical Shear at Wall: $V_{	ext{wall}} = q \cdot B_c$

     * Bending Moment at Wall Face: $M_{	ext{wall}} = rac{q \cdot B_c^2}{2}$

     * Horizontal Axial Tension/Compression at Wall: $H_{	ext{wall}} = \max(F_p,\ p_{	ext{fascia}} \cdot d_f \cdot S_b)$

   * **Case B: Pinned Wall Ledger + Diagonal Tie-Back Hanger Rod (`TieBack_Hanger`)** attached at distance $L_{	ext{rod}}$ from wall and vertical height $H_{	ext{rod}}$ above canopy on the wall (\$	anlpha = H\_{	ext{rod}} / L\_{	ext{rod}}$):

     * Vertical Reaction at Outer Tie-Rod Node: $R_{	ext{rod},y} = rac{q \cdot B_c^2}{2 \cdot L_{	ext{rod}}}$

     * Axial Force in Diagonal Tie-Rod (Tension under downward load; Compression/Buckling or Rod Uplift under net upward wind $0.6D + 0.6W_{	ext{uplift}}$):
       

       $$
       T_{	ext{rod}} = rac{R_{	ext{rod},y}}{\sinlpha}
       $$

     * Upper Wall Eye-Bolt Pullout (Horizontal Tension): $H_{	ext{upper}} = R_{	ext{rod},y} \cdot \cotlpha = rac{q \cdot B_c^2}{2 \cdot H_{	ext{rod}}}$

     * Lower Wall Ledger Compression & Vertical Shear: $C_{	ext{ledger}} = H_{	ext{upper}}$, $V_{	ext{ledger}} = q \cdot B_c - R_{	ext{rod},y}$

3. Apply governing ASD and LRFD load combinations from `ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv` ([ASCE 7-22 Chapter 2](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)):

   * **Governing Downward (ASD)**: $\max\left(D + L_r,\ D + 0.6W_{+},\ D + 0.75L_r + 0.45W_{+} ight)$

   * **Governing Net Uplift (ASD)**: $0.6D + 0.6W_{-}$ (if net upward reaction occurs, slender tie-rods cannot resist compression unless sized as struts; provide hold-down brackets or compression struts).

## 4. Output DTO (`AwningCanopyOutputDTO`) & Downstream Routing

* `q_h_psf`: Velocity pressure at mean roof height $h$ ($ext{psf}$)

* `GCp_net_pos`, `GCp_net_neg`: Interpolated net pressure coefficients from `Figure 30.11-1B`

* `p_net_pos_psf`, `p_net_neg_psf`: Unfactored net downward and upward wind pressures ($ext{psf}$)

* `Fp_lbs`: Horizontal nonstructural seismic force per bracket ($ext{lbs}$)

* `V_wall_ASD`, `M_wall_ASD`, `T_rod_ASD`, `H_upper_ASD`: Governing ASD wall connection reactions

* `V_wall_LRFD`, `M_wall_LRFD`, `T_rod_LRFD`, `H_upper_LRFD`: Governing LRFD wall connection reactions

* **Downstream Connection Modules**:

  * Wood stud/header wall attachment $ightarrow$ `nds/wood_lag_screw_calc.py`

  * Steel bracket weld & bolt plate $ightarrow$ `aisc360/steel_weld_bolt_calc.py`

  * Concrete / CMU wall anchor bolt $ightarrow$ `aci318/concrete_anchor_bolt_calc.py`

## 5. Reference Verification Example

* **Input**: Attached flat steel canopy ($B_c = 5.0	ext{ ft}$, bracket spacing $S_b = 6.0	ext{ ft}$, $h_c = 10.0	ext{ ft}$) on a building with $h = h_e = 20.0	ext{ ft}$, Exposure C, $V = 115	ext{ mph}$, $K_{zt} = 1.0$, $K_e = 1.0$, $w_D = 12	ext{ psf}$, $w_{Lr} = 20	ext{ psf}$, $S_{DS} = 1.0g$.

* **Calculation**:

  1. $r_h = h_c / h_e = 10 / 20 = 0.50 < 0.90$; $A_{	ext{frame}} = 5.0 	imes 6.0 = 30.0	ext{ ft}^2$.

  2. At $h = 20	ext{ ft}$ (Exp C), $K_h = 0.90 \implies q_h = 0.00256 	imes 0.90 	imes 1.0 	imes 1.0 	imes 115^2 = 30.47	ext{ psf}$.

  3. From `Figure 30.11-1B` at $h_c/h_e = 0.50$ and $A = 30	ext{ ft}^2$ ($\log_{10}(30) = 1.477$):

     * $(GC_p)_{	ext{net},+} = 1.87 - 0.47(1.477) = +1.18 \implies p_{	ext{net},+} = 30.47 	imes 0.85 	imes 1.18 = +30.56	ext{ psf}$

     * $(GC_p)_{	ext{net},-} = -2.17 + 0.47(1.477) = -1.48 \implies p_{	ext{net},-} = 30.47 	imes 0.85 	imes (-1.48) = -38.33	ext{ psf}$

  4. **ASD Net Uplift Check per Bracket**:

     * $q_{	ext{up,ASD}} = (0.6 	imes 12.0 - 0.6 	imes 38.33) 	imes 6.0	ext{ ft} = (7.20 - 23.00) 	imes 6.0 = -94.8	ext{ plf}$ (Net upward uplift).

     * Cantilever moment at wall $M_{	ext{up,ASD}} = 94.8 	imes 5.0^2 / 2 = 1,185	ext{ lb-ft}$ upward overturning.