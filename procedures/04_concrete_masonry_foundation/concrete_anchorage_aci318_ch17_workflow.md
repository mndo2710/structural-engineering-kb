# Concrete Anchorage Design Procedure: Cast-In, Mechanical & Adhesive Anchors (ACI 318-19/25 Chapter 17)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 19 (Section 1901.3).
  - **ACI 318-19 / ACI 318-25**: *Building Code Requirements for Structural Concrete*, Chapter 17 (Anchoring to Concrete) ([HALFEN / ACI 318-19 Ch. 17 Reference](https://www.scribd.com/document/980441398/esr-1008), [SteelSolver ACI 318-19 Calculator](https://www.steelsolver.com/p/anchor-bolt-tension-calculator.html)).
  - **ACI 355.2 & ACI 355.4**: Qualification of Post-Installed Mechanical and Adhesive Anchors in Concrete.
  - **Simpson Strong-Tie Anchoring Systems (C-A-2023 & C-C-2026)**: [Titen HD Screw Anchors (ICC-ES ESR-2713)](https://www.strongtie.com/screwanchors_mechanicalanchoringproducts/thd_anchor/p/titen-hd), [SET-3G Epoxy Adhesive Anchors (ICC-ES ESR-4057)](https://www.strongtie.com/epoxyanchoringadhesives_adhesives/set-3g_adhesive/p/set-3g) ([ESR-4057 PDF](https://icc-es.org/wp-content/uploads/report-directory/ESR-4057.pdf)), and [PAB Pre-Assembled Anchor Bolts](https://www.strongtie.com/urscomponents_upliftrestraintsystem/pab_bolt/p/pab).
- **Referenced Repository Databases**:
  - `database/aci_318_tms_402/aci_318_19/ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv`
  - `database/aci_318_tms_402/aci_318_19/ASTM_F1554_and_Headed_Anchor_Bolt_Properties.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv`
- **Design Philosophy**:
  - ACI 318 Chapter 17 is formulated exclusively in **Strength Design (LRFD)** ($N_{ua} \le \phi N_n$, $V_{ua} \le \phi V_n$). When checking against ASD service load demands (e.g. from wood holdowns `HDU` or ASD steel reactions), either factor the loads to LRFD combinations ($1.2D + 1.0E$ or $0.9D + 1.0W/1.0E$) OR multiply the ACI 318 LRFD concrete capacity by $0.70$ (Seismic) or $0.60$ (Wind) per Simpson Strong-Tie PAB conversion notes.

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $N_{ua}, V_{ua}$ | Factored tensile ($N_{ua}$) and shear ($V_{ua}$) demands on anchor or group | $\text{lbs}$ or $\text{kips}$ | ASCE 7-22 LRFD Combinations |
| $N_{ua,s}$ | Factored **sustained** tensile load ($1.2D + 1.6L_{sustained}$) for adhesive anchors | $\text{lbs}$ or $\text{kips}$ | ACI 318-19 Sec. 17.5.2.2 |
| $e'_N, e'_V$ | Eccentricity of resultant tension ($e'_N$) or shear ($e'_V$) relative to anchor group centroid | $\text{in.}$ | Base Plate / Fixture Equilibrium |
| $d_a, h_{ef}$ | Anchor nominal diameter ($d_a$) and effective embedment depth ($h_{ef}$) | $\text{in.}$ | `ASTM_F1554_...csv` / `Simpson_C-A-2023_...csv` |
| $f'_c, \lambda_a$ | Concrete compressive strength ($\text{psi}$) and lightweight factor ($1.0$ normal-weight) | $\text{psi}$ | Structural General Notes |
| $c_{a1}, c_{a2}, s, h_a$ | Edge distances ($c_{a1}, c_{a2}$), anchor spacing ($s$), and member thickness ($h_a$) | $\text{in.}$ | Foundation / Slab Detailing |
| $\text{Cracked}, \text{Cond.}$ | Concrete cracking state (Cracked vs. Uncracked) & Condition A vs. B | — | ACI 318-19 Table 17.5.3 |

---

## 3. Resistance Factors ($\phi$) & Modification Factors ($\psi$)

### 3.1 Resistance Factors ($\phi$, ACI 318-19 Table 17.5.3)
- **Steel Strength**:
  - **Ductile Steel** (ASTM F1554 Gr. 36/55/105, A307, Gr. 60 Rebar): $\phi_{tension} = 0.75$, $\phi_{shear} = 0.65$.
  - **Brittle Steel** (High-strength heat-treated screw anchors e.g. Titen HD): $\phi_{tension} = 0.65$, $\phi_{shear} = 0.60$.
- **Concrete Breakout & Side-Face Blowout**:
  - **Condition A** (Supplementary reinforcement present in failure plane): $\phi = 0.75$ (Cast-in & Post-installed Cat. 1).
  - **Condition B** (No supplementary reinforcement): $\phi = 0.70$ (Cast-in & Post-installed Cat. 1), $0.65$ (Cat. 2), $0.55$ (Cat. 3).
- **Pullout ($N_{pn}$) & Pryout ($V_{cp}$)**: Always **Condition B** ($\phi = 0.70$ for Cast-in & Cat. 1).
- **Adhesive Bond ($N_a, N_{ag}$)**: $\phi = 0.65$ (Cat. 1), $0.55$ (Cat. 2), $0.45$ (Cat. 3).

### 3.2 Concrete Breakout & Bond Modification Factors
- **Eccentricity Factor ($\psi_{ec,N}$, Sec. 17.6.2.3)**: $\psi_{ec,N} = \frac{1}{1 + \frac{2 e'_N}{3 h_{ef}}} \le 1.00$
- **Edge Effect Factor ($\psi_{ed,N}$, Sec. 17.6.2.4)**: If $c_{a,min} \ge 1.5 h_{ef}$, $\psi_{ed,N} = 1.0$; else $\psi_{ed,N} = 0.7 + 0.3 \left(\frac{c_{a,min}}{1.5 h_{ef}}\right)$.
- **Cracking Factor ($\psi_{c,N}$, Sec. 17.6.2.5)**: Cracked $= 1.0$; Uncracked $= 1.25$ (Cast-in, $k_c = 24$) or $1.40$ (Post-installed, $k_c = 17$).
- **Splitting Factor ($\psi_{cp,N}$, Sec. 17.6.2.6)**: $1.0$ for Cast-in; for Post-installed uncracked, $\max(c_{a,min}/c_{ac}, \; 1.5 h_{ef}/c_{ac}) \le 1.0$.

---

## 4. Step-by-Step Calculation Procedure (ACI 318-19 Chapter 17)

### Step 1: Steel Strength in Tension ($\phi N_{sa}$, Sec. 17.6.1)
$$\phi N_{sa} = \phi \cdot n \cdot A_{se,N} \cdot f_{uta}, \qquad f_{uta} \le \min(1.9 f_{ya}, \; 125,000\text{ psi})$$

### Step 2: Concrete Breakout Strength in Tension ($\phi N_{cb}, \phi N_{cbg}$, Sec. 17.6.2)
1. **Single Anchor Projected Area**: $A_{Nco} = 9 h_{ef}^2$.
2. **Actual Projected Area ($A_{Nc}$)**: Rectangular prism extending $\min(c_{a}, 1.5 h_{ef})$ toward free edges and $s$ between anchors:
   $$A_{Nc} = \left(c_{a1,left} + s_x + c_{a1,right}\right) \cdot \left(c_{a2,top} + s_y + c_{a2,bot}\right) \le n \cdot A_{Nco}$$
   *(Note: If three or more edges are $< 1.5 h_{ef}$, use effective embedment $h'_{ef} = \max(c_{a,max}/1.5, \; s_{max}/3)$ per Sec. 17.6.2.1.2).*
3. **Basic Concrete Breakout Strength ($N_b$)**:
   $$N_b = k_c \cdot \lambda_a \cdot \sqrt{f'_c} \cdot h_{ef}^{1.5} \quad (k_c = 24\text{ Cast-in}, \; 17\text{ Post-installed})$$
   *(For cast-in anchors with $11\text{ in.} \le h_{ef} \le 25\text{ in.}$, $N_b = 16 \lambda_a \sqrt{f'_c} h_{ef}^{5/3}$).*
4. **Nominal & Design Breakout Capacity**:
   $$\phi N_{cbg} = \phi \cdot \left(\frac{A_{Nc}}{A_{Nco}}\right) \cdot \psi_{ec,N} \cdot \psi_{ed,N} \cdot \psi_{c,N} \cdot \psi_{cp,N} \cdot N_b$$

### Step 3: Pullout ($\phi N_{pn}$), Side-Face Blowout ($\phi N_{sb}$), & Adhesive Bond ($\phi N_a$)
1. **Pullout (Sec. 17.6.3)**:
   - Headed Bolt/Stud: $\phi N_{pn} = 0.70 \cdot \psi_{c,P} \cdot (8 A_{brg} f'_c)$ ($\psi_{c,P} = 1.0$ cracked, $1.4$ uncracked).
   - Post-installed Screw Anchor (e.g. `Titen HD`): Look up $N_{p,cr}$ / $N_{p,uncr}$ from `Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv`.
2. **Side-Face Blowout (Sec. 17.6.4, when $h_{ef} > 2.5 c_{a1}$)**:
   $$\phi N_{sb} = \phi \cdot 160 \cdot c_{a1} \cdot \sqrt{A_{brg}} \cdot \lambda_a \cdot \sqrt{f'_c}$$
3. **Adhesive Bond Strength (Sec. 17.6.5, e.g. `SET-3G` ESR-4057)**:
   $$c_{Na} = 10 d_a \sqrt{\frac{\tau_{uncr}}{1100}}, \qquad A_{Nao} = (2 c_{Na})^2, \qquad N_{ba} = \lambda_a \cdot \tau_k \cdot \pi \cdot d_a \cdot h_{ef}$$
   $$\phi N_{ag} = \phi \cdot \left(\frac{A_{Na}}{A_{Nao}}\right) \cdot \psi_{ec,Na} \cdot \psi_{ed,Na} \cdot \psi_{cp,Na} \cdot N_{ba}$$
   - **Sustained Tension Check (Sec. 17.5.2.2)**: Verify $N_{ua,s} \le 0.55 \cdot \phi \cdot N_{ba}$.

### Step 4: Shear Limit States ($\phi V_{sa}, \phi V_{cbg}, \phi V_{cpg}$, Sec. 17.7)
1. **Steel Shear (Sec. 17.7.1)**: $\phi V_{sa} = 0.65 \cdot (0.60 A_{se,V} f_{uta}) \cdot (0.80 \text{ if grout pad})$.
2. **Concrete Shear Breakout (Sec. 17.7.2)**:
   $$A_{Vco} = 4.5 c_{a1}^2, \qquad V_b = \min\left(7\left(\frac{l_e}{d_a}\right)^{0.2} \sqrt{d_a}, \; 9\right) \lambda_a \sqrt{f'_c} c_{a1}^{1.5}$$
   $$\phi V_{cbg} = \phi \cdot \left(\frac{A_{Vc}}{A_{Vco}}\right) \cdot \psi_{ec,V} \cdot \psi_{ed,V} \cdot \psi_{c,V} \cdot \psi_{h,V} \cdot V_b$$
3. **Concrete Pryout (Sec. 17.7.3)**: $\phi V_{cpg} = 0.70 \cdot k_{cp} \cdot N_{cpg}$ ($k_{cp} = 1.0$ if $h_{ef} < 2.5"$; $2.0$ if $h_{ef} \ge 2.5"$).

### Step 5: Tension-Shear Interaction (Sec. 17.8) & Seismic Checks (Sec. 17.10)
- **Interaction**: Check $\frac{N_{ua}}{\phi N_n} + \frac{V_{ua}}{\phi V_n} \le 1.20$ (or $\left(\frac{N_{ua}}{\phi N_n}\right)^{5/3} + \left(\frac{V_{ua}}{\phi V_n}\right)^{5/3} \le 1.00$).
- **Seismic (SDC C–F)**: For non-ductile concrete modes in tension, check $N_{ua} \le 0.75 \cdot \phi N_{n,concrete}$ (unless designed for $\Omega_0$ overstrength or controlled by ductile steel yielding with stretch length $\ge 8 d_a$).

---

## 5. Limit States Summary Table

| Limit State | Equation Reference | $\phi$ (Condition B) | Governing Check |
| :--- | :--- | :--- | :--- |
| **Steel Tension ($N_{sa}$)** | ACI 318 Eq. 17.6.1.2 | $0.75$ (Ductile) / $0.65$ (Brittle) | $N_{ua} / (\phi N_{sa}) \le 1.00$ |
| **Concrete Breakout ($N_{cbg}$)** | ACI 318 Eq. 17.6.2.1b | $0.70$ (SDC C-F: $\times 0.75$) | $N_{ua} / (\phi N_{cbg}) \le 1.00$ |
| **Anchor Pullout ($N_{pn}$)** | ACI 318 Eq. 17.6.3.1 | $0.70$ (SDC C-F: $\times 0.75$) | $N_{ua} / (\phi N_{pn}) \le 1.00$ |
| **Side-Face Blowout ($N_{sb}$)** | ACI 318 Eq. 17.6.4.1 | $0.70$ (SDC C-F: $\times 0.75$) | $N_{ua} / (\phi N_{sb}) \le 1.00$ |
| **Adhesive Bond ($N_{ag}$)** | ACI 318 Eq. 17.6.5.1b | $0.65$ (Cat. 1) | $N_{ua} / (\phi N_{ag}) \le 1.00$ |
| **Steel Shear ($V_{sa}$)** | ACI 318 Eq. 17.7.1.2b | $0.65$ (Ductile) / $0.60$ (Brittle) | $V_{ua} / (\phi V_{sa}) \le 1.00$ |
| **Concrete Shear Breakout ($V_{cbg}$)** | ACI 318 Eq. 17.7.2.1b | $0.70$ | $V_{ua} / (\phi V_{cbg}) \le 1.00$ |
| **Concrete Pryout ($V_{cpg}$)** | ACI 318 Eq. 17.7.3.1b | $0.70$ | $V_{ua} / (\phi V_{cpg}) \le 1.00$ |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **3-Edge Truncation Rule ($h'_{ef}$, ACI 318-19 Sec. 17.6.2.1.2)**: When a holdown anchor bolt is placed in a narrow stemwall or grade beam ($b_{stem} = 6"$ or $8"$) near a corner where 3 edges are $< 1.5 h_{ef}$, raw $h_{ef}$ **cannot** be used in $N_b$ and $A_{Nco}$! You must substitute $h'_{ef} = \max(c_{a,max}/1.5, s/3)$, OR provide **U-bar / Hairpin Anchor Reinforcement** per Sec. 17.5.2.1 (`Simpson L-L-RODSTWALL26`).
2. **Adhesive Anchor Hole Cleaning & Special Inspection**: Specify periodic/continuous special inspection per IBC Table 1705.3 and ICC-ES ESR-4057 (`SET-3G`), especially for overhead, water-filled, or deep holes.
3. **J-Bolts Prohibited for High Tension**: Hooked J/L-bolts have very low pullout strength ($N_p = 0.9 f'_c e_h d_a$). Always specify headed bolts (`ASTM F1554` with heavy hex nut or `Simpson PAB` with plate washer).

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Verify a **single `5/8"` dia. ASTM F1554 Gr. 36 cast-in headed anchor bolt** (with Heavy Hex nut, $A_{se,N} = 0.226\text{ in.}^2, A_{brg} = 1.01\text{ in.}^2$, $h_{ef} = 9.0\text{ in.}$) anchoring a wood shear wall holdown (`HDU4-SDS2.5`) in an interior concrete slab/footing ($f'_c = 3,000\text{ psi}$ cracked concrete, Condition B, SDC D, $c_{a,min} = 12.0" < 1.5 h_{ef} = 13.5"$, other edges $\ge 13.5"$):
- **Applied Tension**: ASD Seismic $T_{ASD} = 3,150\text{ lbs} \implies$ LRFD Seismic $N_{ua} = T_{ASD} / 0.70 = 4,500\text{ lbs}$ ($4.50\text{ kips}$).
1. **Steel Tension ($\phi N_{sa}$)**:
   $$\phi N_{sa} = 0.75 \times 0.226 \times 58,000 = 9,831\text{ lbs} \ge 4,500\text{ lbs} \quad (D/C = 0.458) \implies \textbf{OK}$$
2. **Concrete Breakout in Tension ($\phi N_{cb}$)**:
   - $A_{Nco} = 9(9.0)^2 = 729.0\text{ in.}^2$; $A_{Nc} = (12.0 + 13.5) \times (27.0) = 688.5\text{ in.}^2 \implies A_{Nc}/A_{Nco} = 0.944$.
   - $\psi_{ed,N} = 0.7 + 0.3(12.0 / 13.5) = 0.967$; $\psi_{c,N} = 1.0$ (cracked); $N_b = 24(1.0)\sqrt{3000}(9.0)^{1.5} = 35,492\text{ lbs}$.
   - With SDC D $0.75$ seismic factor and $\phi = 0.70$ (Condition B):
     $$0.75 \phi N_{cb} = 0.75 \times 0.70 \times 0.944 \times 0.967 \times 1.0 \times 35,492 = 17,010\text{ lbs} \ge 4,500\text{ lbs} \implies \textbf{OK}$$
3. **Concrete Pullout ($\phi N_{pn}$)**:
   $$0.75 \phi N_{pn} = 0.75 \times 0.70 \times 1.0 \times (8 \times 1.01 \times 3,000) = 12,726\text{ lbs} \ge 4,500\text{ lbs} \quad (D/C = 0.354) \implies \textbf{OK}$$
