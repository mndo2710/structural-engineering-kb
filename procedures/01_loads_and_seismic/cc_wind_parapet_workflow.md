# Design Procedure: Components and Cladding (C&C) & MWFRS Wind Loads on Parapets (ASCE 7-22)

## 1. Scope & Code References
- **Governing Codes**: 2024 IBC / 2025 CBC Chapter 16; [ASCE/SEI 7-22](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784415788/part/provisions/standard-chapter/s26/standard-sec-ver/s26.10.1.ver.atom) Chapters 26, 27, and 30.
- **Specific Provisions**:
  - **ASCE 7-22 Section 26.10**: Velocity Pressure ($q_z$, $q_h$, $q_p$).
  - **ASCE 7-22 Section 27.3.4**: Main Wind Force Resisting System (MWFRS) Design Wind Load on Parapets ($p_p$).
  - **[ASCE 7-22 Section 30.9](https://www.scribd.com/document/254619812/ASCE-WIND-LOAD-EXAMPLES-pdf)**: Components and Cladding (C&C) Design Wind Pressures on Parapets (Figure 30.9-1).
- **Application**: Wood-framed or steel cantilever parapet studs/posts, parapet sheathing, cap flashing, and roof-to-wall parapet connections in low-rise buildings ($h \le 60\text{ ft}$).

## 2. Required Database CSV Tables (`database/asce_7/v7_22/`)
- `ASCE7-22_Table_26.6-1.csv`: Wind Directionality Factor ($K_d = 0.85$ for Buildings MWFRS and C&C).
- `ASCE7-22_Table_26.9-1.csv`: Ground Elevation Factor ($K_e$).
- `ASCE7-22_Table_26.10-1.csv`: Velocity Pressure Exposure Coefficients ($K_p$ evaluated at top of parapet $z = h_p$).
- `ASCE7-22_Table_26.13-1.csv`: Internal Pressure Coefficient ($GC_{pi}$) for enclosed/partially enclosed parapet cavities.
- `ASCE7-22_Table_C30.3-1.csv`: External Wall Pressure Coefficients ($GC_p$) for Zones 4 and 5 (Figure 30.3-1).
- `ASCE7-22_Table_C30.3-2_C30.3-3.csv`: External Roof Pressure Coefficients ($GC_p$) for Zones 1, 2, and 3 (Figures 30.3-2A/B).

## 3. Input Parameters
| Symbol | Parameter Description | Unit | Notes / Default |
| :--- | :--- | :--- | :--- |
| $V$ | Basic Wind Speed | $\text{mph}$ | Per Risk Category (ASCE 7-22 Figures 26.5-1A to 1D) |
| $\text{Exp}$ | Exposure Category | - | B, C, or D (Section 26.7) |
| $h$ | Mean Roof Height | $\text{ft}$ | Used for roof zone width $a$ |
| $h_{par}$ | Parapet Cantilever Height above Roof | $\text{ft}$ | Measured from roof surface to top of parapet |
| $h_p$ | Total Height to Top of Parapet | $\text{ft}$ | $h_p = h + h_{par}$ |
| $s$ | Parapet Stud / Post Spacing | $\text{ft}$ | Typical $1.33\text{ ft}$ ($16\text{ in.}$) or $2.0\text{ ft}$ ($24\text{ in.}$) |
| $\theta$ | Roof Slope | $\text{deg}$ | Degrees |
| $K_{zt}$ | Topographic Factor | - | Default $= 1.0$ (Section 26.8) |
| $z_e$ | Site Ground Elevation above Sea Level | $\text{ft}$ | Default $= 0\text{ ft}$ ($K_e = 1.00$) |

## 4. Step-by-Step Calculation Equations (ASD & LRFD)

### Step 4.1: Effective Wind Area ($A$) of Parapet Framing Element
For a vertical parapet stud or cantilever post spanning $L_{span} = h_{par}$ spaced at $s$:
$$b_{eff} = \max\left(s, \frac{h_{par}}{3}\right)$$
$$A = h_{par} \cdot b_{eff} \quad (\text{ft}^2)$$
*(For parapet sheathing/cladding, take $A = 10\text{ ft}^2$ conservative cutoff).*

### Step 4.2: Velocity Pressure at Top of Parapet ($q_p$)
Lookup $K_p = K_z$ at height $z = h_p$ from `ASCE7-22_Table_26.10-1.csv`, $K_d = 0.85$ from `ASCE7-22_Table_26.6-1.csv`, and $K_e$ from `ASCE7-22_Table_26.9-1.csv`.
Per ASCE 7-22 Equation (26.10-1) (Note: $K_d$ is removed from $q_z$ in ASCE 7-22 and placed into pressure equations, or combined directly as $q_p \cdot K_d$):
$$q_p = 0.00256 \cdot K_p \cdot K_{zt} \cdot K_e \cdot V^2 \quad (\text{psf})$$

### Step 4.3: MWFRS Parapet Pressure ($p_p$ - Global Framing Check)
Per ASCE 7-22 Equation (27.3-4):
$$p_p = q_p \cdot K_d \cdot (GC_{pn}) \quad (\text{psf})$$
- **Windward Parapet**: $GC_{pn} = +1.5$ (net pressure acting inward toward roof).
- **Leeward Parapet**: $GC_{pn} = -1.0$ (net pressure acting outward away from roof).

### Step 4.4: C&C Parapet Pressures ($p$ - Local Stud, Sheathing & Connection Check)
Per [ASCE 7-22 Section 30.9](https://www.scribd.com/document/254619812/ASCE-WIND-LOAD-EXAMPLES-pdf), Equation (30.9-1):
$$p = q_p \cdot K_d \cdot \left[(GC_p) - (GC_{pi})\right] \quad (\text{psf})$$
Two load cases must be evaluated simultaneously across the front (exterior wall) and back (roof-side) surfaces of the parapet:

1. **Load Case A (Windward Parapet - Inward Bending)**:
   - **Front Face (Exterior Wall Surface)**: Apply positive wall $(GC_p)^+$ from `ASCE7-22_Table_C30.3-1.csv` (Zone 4 or 5).
   - **Back Face (Interior/Roof Surface)**: Apply negative roof $(GC_p)^-$ from `ASCE7-22_Table_C30.3-2_C30.3-3.csv` (Zone 2 or 3 adjacent to parapet).
   - **Combined Net Pressure on Framing Member**: When a single parapet stud supports both front and back sheathing, internal pressure $(GC_{pi})$ inside the enclosed parapet cavity cancels out for total member bending, yielding:
     $$p_{net,A} = q_p \cdot K_d \cdot \left[ |(GC_p)_{wall}^+| + |(GC_p)_{roof}^-| \right] \quad (\text{psf})$$
     *(Note: If the roof slope $\theta \le 10^\circ$, wall $(GC_p)$ values are reduced by $10\%$ per Figure 30.3-1 Note 5).*

2. **Load Case B (Leeward Parapet - Outward Bending)**:
   - **Front Face (Exterior Wall Surface)**: Apply negative wall $(GC_p)^-$ from `ASCE7-22_Table_C30.3-1.csv` (Zone 4 or 5).
   - **Back Face (Interior/Roof Surface)**: Apply positive roof $(GC_p)^+$ from `ASCE7-22_Table_C30.3-2_C30.3-3.csv` (Zone 2 or 3).
   - **Combined Net Pressure on Framing Member**:
     $$p_{net,B} = q_p \cdot K_d \cdot \left[ |(GC_p)_{wall}^-| + |(GC_p)_{roof}^+| \right] \quad (\text{psf})$$

3. **Individual Cladding / Sheathing Fastener Check**:
   - Fasteners attaching sheathing to one side of a hollow framed parapet must include internal cavity pressure $(GC_{pi}) = \pm 0.18$ (or $\pm 0.55$ if partially enclosed):
     $$p_{cladding} = q_p \cdot K_d \cdot \left[ (GC_p) - (\pm GC_{pi}) \right] \quad (\text{psf})$$

### Step 4.5: Cantilever Parapet Base Shear & Moment Demands
For Governing C&C Net Pressure $p_{gov} = \max(p_{net,A}, p_{net,B})$ and ASD factor $0.6W$ (or LRFD $1.0W$):
- **ASD Line Load on Post/Stud**:
  $$w_{ASD} = 0.6 \cdot p_{gov} \cdot s \quad (\text{plf})$$
- **ASD Cantilever Base Shear (at Roof Diaphragm Line)**:
  $$V_{base,ASD} = w_{ASD} \cdot h_{par} \quad (\text{lbs})$$
- **ASD Cantilever Base Moment (at Roof Diaphragm Line)**:
  $$M_{base,ASD} = \frac{w_{ASD} \cdot h_{par}^2}{2} \quad (\text{lb-ft})$$
- **Continuous Balloon-Stud Backspan Reaction (if stud is continuous down to floor/header below with backspan $L_{back}$)**:
  $$R_{roof,ASD} = V_{base,ASD} \cdot \left(1 + \frac{h_{par}}{2 \cdot L_{back}}\right) \quad (\text{lbs})$$

## 5. Governing Checks & Warnings
- **Minimum Design Wind Load Check**: Per ASCE 7-22 Section 30.2.2, the design wind pressure for C&C shall not be less than $16\text{ psf}$ acting in either direction normal to the surface.
- **Parapet Height Relief on Roof Zone 3**: Per Figure 30.3-2A Note 5, if $h_{par} \ge 3.0\text{ ft}$ around the perimeter of a low-slope roof ($\theta \le 7^\circ$), negative $(GC_p)$ in Corner Zone 3 is permitted to be taken equal to Edge Zone 2.
- **Spliced Stud Warning**: Never splice parapet studs at the roof line without a dedicated moment connection (e.g., steel tube post, Simpson strap pair on opposite faces, or continuous balloon stud extending at least $2 \cdot h_{par}$ below the roof diaphragm).
