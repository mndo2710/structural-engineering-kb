# Design Procedure: Components and Cladding (C&C) Wind Loads on Roof Overhangs (ASCE 7-22)

## 1. Scope & Code References
- **Governing Codes**: 2024 IBC / 2025 CBC Chapter 16; [ASCE/SEI 7-22](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784415788/part/provisions/standard-chapter/s26/standard-sec-ver/s26.10.1.ver.atom) Chapters 26 and 30.
- **Specific Provisions**:
  - **[ASCE 7-22 Section 30.7](https://www.structuremag.org/article/asce-7-22-changes-to-component-and-cladding-wind-provisions/)**: Roof Overhangs (Figure 30.7-1).
  - **ASCE 7-22 Section 30.3**: Low-Rise Building External Pressure Coefficients ($h \le 60\text{ ft}$).
- **Major Code Change in ASCE 7-22**: Separate overhang $(GC_p)$ charts from ASCE 7-16 were removed. Per [ASCE 7-22 Section 30.7 and Figure 30.7-1](https://www.structuremag.org/article/asce-7-22-changes-to-component-and-cladding-wind-provisions/), roof overhang pressures are determined by combining the external pressure on the **top surface of the roof overhang** with the adjacent **positive wall pressure acting upward on the bottom soffit surface**.
- **Application**: Rafter tails, lookout rafters, cantilevered roof beams, fascia boards, soffit cladding, and hurricane tie / rafter-to-top-plate uplift connections (e.g., Simpson H2.5A, H1, HDU).

## 2. Required Database CSV Tables (`database/asce_7/v7_22/`)
- `ASCE7-22_Table_26.6-1.csv`: Wind Directionality Factor ($K_d = 0.85$).
- `ASCE7-22_Table_26.9-1.csv`: Ground Elevation Factor ($K_e$).
- `ASCE7-22_Table_26.10-1.csv`: Velocity Pressure Exposure Coefficients ($K_h$ evaluated at mean roof height $h$).
- `ASCE7-22_Table_C30.3-1.csv`: External Wall Pressure Coefficients ($GC_p$) for Zones 4 and 5 (Figure 30.3-1).
- `ASCE7-22_Table_C30.3-2_C30.3-3.csv`: External Roof Pressure Coefficients ($GC_p$) for Zones 1, 2, and 3 (Figures 30.3-2A/B).

## 3. Input Parameters
| Symbol | Parameter Description | Unit | Notes / Default |
| :--- | :--- | :--- | :--- |
| $V$ | Basic Wind Speed | $\text{mph}$ | Per Risk Category |
| $\text{Exp}$ | Exposure Category | - | B, C, or D |
| $h$ | Mean Roof Height | $\text{ft}$ | $h \le 60\text{ ft}$ for Part 1 (Low-Rise) |
| $L_{oh}$ | Horizontal Overhang Projection | $\text{ft}$ | Measured from exterior wall face to fascia |
| $L_{back}$ | Rafter / Beam Interior Backspan | $\text{ft}$ | Span from exterior wall to first interior support |
| $s$ | Rafter / Lookout Spacing | $\text{ft}$ | Typical $1.33\text{ ft}$ ($16\text{ in.}$) or $2.0\text{ ft}$ ($24\text{ in.}$) |
| $\theta$ | Roof Slope | $\text{deg}$ | Degrees |
| $K_{zt}$ | Topographic Factor | - | Default $= 1.0$ |
| $z_e$ | Site Ground Elevation above Sea Level | $\text{ft}$ | Default $= 0\text{ ft}$ ($K_e = 1.00$) |

## 4. Step-by-Step Calculation Equations (ASD & LRFD)

### Step 4.1: Velocity Pressure at Mean Roof Height ($q_h$)
Lookup $K_h$ at $z = h$ from `ASCE7-22_Table_26.10-1.csv`, $K_d = 0.85$ from `ASCE7-22_Table_26.6-1.csv`, and $K_e$ from `ASCE7-22_Table_26.9-1.csv`:
$$q_h = 0.00256 \cdot K_h \cdot K_{zt} \cdot K_e \cdot V^2 \quad (\text{psf})$$

### Step 4.2: Effective Wind Area ($A$)
- **For Overhang Framing Member only (Cantilever Check)**:
  $$A_{oh} = \max\left(L_{oh} \cdot s, \frac{L_{oh}^2}{3}\right) \quad (\text{ft}^2)$$
- **For Full Rafter + Overhang Holdown/Tie Uplift at Exterior Wall**:
  $$L_{total} = L_{back} + L_{oh}$$
  $$A_{rafter} = \max\left(L_{total} \cdot s, \frac{L_{total}^2}{3}\right) \quad (\text{ft}^2)$$

### Step 4.3: Combined Overhang Pressure Coefficient $(GC_p)_{oh}$ per Section 30.7
Per [ASCE 7-22 Section 30.7 and Figure 30.7-1](https://www.structuremag.org/article/asce-7-22-changes-to-component-and-cladding-wind-provisions/):
1. **Top Roof Surface Contribution $(GC_p)_{roof}$**:
   Lookup negative (uplift) or positive (downward) $(GC_p)_{roof}$ from `ASCE7-22_Table_C30.3-2_C30.3-3.csv` for the applicable roof zone (Zone 2 along eave/rake edge, or Zone 3 at roof corners) using Effective Wind Area $A$.
2. **Bottom Soffit Surface Contribution $(GC_p)_{soffit}$**:
   Per Figure 30.7-1, the pressure coefficient on the underside of the overhang equals the **adjacent wall pressure coefficient** from Figure 30.3-1 (`ASCE7-22_Table_C30.3-1.csv`):
   - Map Roof **Zone 1 or 2** $\rightarrow$ Adjacent Wall **Zone 4** ($(GC_p)_{wall}^+ = +1.0$ at $A \le 10\text{ ft}^2$).
   - Map Roof **Zone 3** (Corner) $\rightarrow$ Adjacent Wall **Zone 5** ($(GC_p)_{wall}^+ = +1.0$ at $A \le 10\text{ ft}^2$).
   *(Note: If $\theta \le 10^\circ$, apply the $0.90$ reduction factor to wall $(GC_p)$ per Figure 30.3-1 Note 5).*
3. **Combined Net Overhang Uplift Coefficient (for structural framing supporting both top and bottom surfaces)**:
   Positive wall pressure washes up the wall and pushes **upward** on the soffit, adding directly to the suction on the top surface. Internal pressure $(GC_{pi})$ cancels out across the overhang:
   $$(GC_p)_{oh,net}^- = (GC_p)_{roof}^- - (GC_p)_{wall}^+$$
   *(Example: For Gable Roof $\theta = 15^\circ$, Zone 2 with $A \le 10\text{ ft}^2$: $(GC_p)_{roof}^- = -2.5$ and $(GC_p)_{wall}^+ = +1.0 \implies (GC_p)_{oh,net}^- = -3.5$).*
4. **Soffit Cladding Only (Underside Panels/Vents)**:
   Per [ASCE 7-22 Section 30.7](https://www.google.com/search?q=https://www.eng-tips.com/threads/asce-7-22-roof-overhang-pressure.519150/), cladding on a single surface only needs its adjacent $(GC_p)_{wall}$ combined with internal soffit cavity pressure $(GC_{pi})$.

### Step 4.4: Design Wind Pressures ($p_{oh}$ and $p_{main}$)
- **Net Uplift Pressure on Overhang ($L_{oh}$)**:
  $$p_{oh} = q_h \cdot K_d \cdot (GC_p)_{oh,net}^- \quad (\text{psf})$$
- **Net Uplift Pressure on Interior Rafter Span ($L_{back}$)**:
  $$p_{main} = q_h \cdot K_d \cdot \left[(GC_p)_{roof}^- - (+GC_{pi})\right] \quad (\text{psf})$$

### Step 4.5: Rafter Cantilever & Wall Tie Uplift Reaction (ASD $0.6D + 0.6W$)
Let $w_{D}$ (plf) be the dead load per linear foot of rafter, $w_{W,oh} = |p_{oh}| \cdot s$ (plf) on the overhang, and $w_{W,main} = |p_{main}| \cdot s$ (plf) on the interior span:
- **Net ASD Uplift Line Load on Overhang**:
  $$w_{net,oh} = 0.6 \cdot w_{W,oh} - 0.6 \cdot w_D \quad (\text{plf})$$
- **Net ASD Uplift Line Load on Interior Span**:
  $$w_{net,main} = 0.6 \cdot w_{W,main} - 0.6 \cdot w_D \quad (\text{plf})$$
- **ASD Cantilever Moment at Exterior Wall Bearing**:
  $$M_{oh,ASD} = \frac{w_{net,oh} \cdot L_{oh}^2}{2} \quad (\text{lb-ft})$$
- **ASD Total Net Uplift Reaction at Exterior Wall Tie/Clip ($R_{uplift,ASD}$)**:
  Taking moments about the interior support (distance $L_{back}$ from the exterior wall):
  $$R_{uplift,ASD} = \frac{w_{net,main} \cdot L_{back}}{2} + w_{net,oh} \cdot L_{oh} \cdot \left(1 + \frac{L_{oh}}{2 \cdot L_{back}}\right) \quad (\text{lbs})$$

## 5. Governing Checks & Warnings
- **Notched Rafter Tail Check (NDS Section 3.4.3)**: If the rafter is notched at the top plate bearing (birdsmouth cut), shear capacity at the notch is reduced by $(d_e / d)^2$ and governs over standard horizontal shear.
- **Minimum C&C Pressure**: Design wind pressure shall not be less than $16\text{ psf}$ per ASCE 7-22 Section 30.2.2.
- **Toe-Nail Prohibition on High Uplift**: When $R_{uplift,ASD} > 150\text{ lbs}$, toe-nails alone are typically insufficient; specify a rated metal hurricane tie (e.g., Simpson H2.5A, H1, or H10A) from `database/manufacturer_catalogs/simpson_strong_tie/`.
