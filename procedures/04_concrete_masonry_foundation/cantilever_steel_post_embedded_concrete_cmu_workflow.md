# Cantilever Steel Post Embedded in Grouted CMU or Concrete Wall Design Procedure (AISC 360 / TMS 402 / ACI 318)

## 1. General & Code Basis
- **System Configuration**: Cantilever structural steel post (HSS square/rectangular tube or Wide-Flange) projecting height $H$ above the top of a reinforced concrete or solidly grouted CMU wall and embedded depth $L_e$ into the wall pocket, with horizontal bond-beam bars or confining U-bars/hairpins welded directly to the steel post webs and a bottom bearing cap plate (no base anchor bolts).
- **Governing Codes & Standards**:
  - **ASCE/SEI 7-22**: Section 2.3 (LRFD) & Section 2.4 (ASD Load Combinations).
  - **ANSI/AISC 360-22**: *Specification for Structural Steel Buildings* ($K = 2.1$ cantilever stability, $t_{des} = 0.93 t_{nom}$, Table J2.2 flare-bevel groove welds, Sec. J4.2 wall shear).
  - **TMS 402/602-22**: Chapter 8 (ASD) & Chapter 9 (SD) — Grout bearing, breakout Eq. 8-2 / 8-7, one-way bond beam shear Sec. 8.3.5.1.2, and global wall interaction Sec. 8.3.4 ([TMS 402 Masonry Anchor Bolt Reference](https://www.scribd.com/document/450073931/Anchor-pdf)).
  - **ACI 318-19 / 318-25 & ACI 315**: Chapter 17 (Out-of-plane shear lug/embedment breakout Sec. 17.7.2 & 17.11.3; Anchor reinforcement Sec. 17.5.2.1; Unpainted embedded steel Sec. 26.5.6.1(d)) & ACI 315 Sec. 2.8.3 (Jamb bar confinement).
  - **AWS D1.4/D1.4M**: *Structural Welding Code—Reinforcing Steel* (ASTM A706 Grade 60 weldable rebar).
- **Referenced Repository Databases**:
  - `database/aci_318_tms_402/aci_318_19/rebar_astm_a615_a706.csv`
  - `database/aci_318_tms_402/tms_402_22/TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv`
  - `database/aci_318_tms_402/aci_318_19/ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv`

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $P_a, V_a, e$ | Applied ASD axial force ($P_a$), lateral shear ($V_a$), and eccentricity ($e$) at post top | $\text{kips}, \text{in.}$ | ASCE 7-22 Load Takedown |
| $H, L_e, a_0$ | Cantilever projection ($H$), embedment depth ($L_e$), unrestrained top spall depth ($a_0 = 1.5"\text{–}2.0"$) | $\text{in.}$ | Framing / Wall Section Detail |
| $H_{HSS} \times B_{HSS} \times t_{nom}$ | Steel post dimensions ($b = B_{HSS}$ contact width), $t_{des} = 0.93 t_{nom}$, $F_y = 50\text{ ksi}$ | $\text{in.}, \text{ksi}$ | ASTM A500 Gr. C / A1085 |
| $t_{wall}, f'_m$ | CMU wall actual thickness ($7.625"$ for $8"$ CMU, $11.625"$ for $12"$ CMU) and $f'_m$ | $\text{in.}, \text{psi}$ | `TMS402-22_Masonry_...csv` |
| $d_b, n_{bars}, z_b$ | Welded horizontal rebar diameter (`#4`, `#5`), bar count per layer, vertical lever arm ($z_b$) | $\text{in.}$ | `rebar_astm_a615_a706.csv` (ASTM A706 Gr. 60) |

---

## 3. Load Path & Force Couple Mechanics ($C_1, C_2$)
1. **Internal Demands at Top of Wall**: $M_a = V_a \cdot H + P_a \cdot e$.
2. **Effective Embedment & Lateral Couple ($C_1$ Top, $C_2$ Bottom)**:
   - Neglecting top spalling zone $a_0 = 1.5"\text{ to }2.0"$: $L'_e = L_e - a_0$, $M'_a = M_a + V_a \cdot a_0$.
   - **Continuous Elastic Grout Bearing Model (TMS 402 Sec. 8.1.2)**:
     $$f_{b,lat} = \frac{V_a}{b \cdot L'_e} + \frac{6 M'_a}{b \cdot (L'_e)^2} \le F_{br} = 0.25 f'_m$$
     $$C_1 = \frac{V_a}{2} + \frac{3 M'_a}{2 L'_e}, \qquad C_2 = C_1 - V_a = \frac{3 M'_a}{2 L'_e} - \frac{V_a}{2}$$
   - **Discrete Welded Rebar Couple Model** (top bar layer at depth $d_{top}$ below wall top, vertical arm $z_b$ between top and bottom welded bar layers):
     $$C_1 = \frac{M_a + V_a (d_{top} + z_b)}{z_b}, \qquad C_2 = \frac{M_a + V_a d_{top}}{z_b}$$

---

## 4. Step-by-Step Calculation Procedure (ASD Method with ACI 318 Reference)

### Step 1: Cantilever HSS Post Member Check (AISC 360 Chapters E, F, G, H)
- Effective buckling length $L_c = K \cdot H = 2.1 H$ (AISC Commentary Table C-A-7.1 for fixed-free cantilever with rotational support flexibility).
- Verify $P_a / P_{all} + \frac{8}{9}(M_{ax}/M_{all,x} + M_{ay}/M_{all,y}) \le 1.00$ (or Eq. H1-1b) and $V_a \le V_{all}$.

### Step 2: Bottom End Bearing Plate ($P_a > 0$) & Net Uplift Dowels ($P_a < 0$)
1. **Compression Bearing Plate ($B_p \times N_p \times t_p$)**:
   $$f_{br,vert} = \frac{P_a}{B_p \cdot N_p} \le F_{br} = 0.25 f'_m, \qquad t_{p,req} = m \sqrt{\frac{3.33 f_{br,vert}}{F_{y,plate}}}$$
2. **Net Uplift ($0.6D + 0.6W$)**: Weld vertical ASTM A706 Gr. 60 dowel bars to HSS webs: $A_{s,uplift} = |P_a| / 32.0\text{ ksi}$.

### Step 3: Welded Horizontal Rebar & Flare-Bevel Groove Weld Design
1. **Required Horizontal Rebar Area (ASTM A706 Grade 60, ASD $F_s = 32.0\text{ ksi}$)**:
   $$A_{s,horiz,req} = \frac{C_1}{32.0\text{ ksi}} \le n_{bars} \cdot A_b$$
2. **Flare-Bevel Groove Weld (AISC Table J2.2 & Sec. J2.4, $\Omega_w = 2.00$, E70XX)**:
   - Effective throat $E = \frac{5}{32} d_b = 0.156 d_b$.
   - Allowable shear per linear inch per side:
     $$q_{w,all} = \frac{0.60 F_{EXX} E}{2.00} = \frac{0.60(70)(0.156 d_b)}{2.00} = 3.281 \cdot d_b \quad (\text{kips/in./side})$$
   - Required weld length per bar ($n_{sides} = 1$ or $2$):
     $$l_{w,req} = \frac{\max(C_1 / n_{bars}, \; 32.0 A_b)}{n_{sides} \cdot q_{w,all}}$$
3. **HSS Connecting Sidewall In-Plane Shear (AISC Sec. J4.2, $\Omega_v = 1.50$)**:
   $$R_{v,all,HSS} = 0.40 \cdot F_{y,HSS} \cdot t_{des} \cdot l_w \ge \frac{C_1}{n_{bars}}$$
4. **Tension Development / Lap Splice Length in CMU (TMS 402 Eq. 8-12)**:
   $$l_d = \frac{0.13 d_b^2 f_y \gamma}{K \sqrt{f'_m}} \ge 12\text{ in.} \quad (\text{Lap splice } l_{lap} = \max(l_d, 48 d_b))$$

### Step 4: Out-of-Plane Masonry Breakout, One-Way Bond Beam Shear & Confining Hairpins
When the cantilever post bends **out-of-plane** (perpendicular to the CMU wall), check all four mechanisms:
1. **Mechanism 4.1 — Out-of-Plane Masonry Breakout Cone (TMS 402 Eq. 8-2 & Eq. 8-7)**:
   - Distance from welded bar/bearing face to outer compression wall surface: $l_b$ ($3.81"$ for centered bar in $8"$ CMU; $5.25"$ for tension-face bar in double curtain).
   - Projected area truncated by top of wall ($c_{top} < l_b$): $A_{pt} = (b_{col} + 2 l_b)(l_b + c_{top})$.
   - Allowable breakout strength:
     $$B_{ab,oop} = 1.25 \cdot A_{pt} \cdot \sqrt{f'_m} \ge C_1 \quad (\text{or Edge Shear Breakout } B_{vb,oop} = 0.625 A_{pv} \sqrt{f'_m})$$
2. **Mechanism 4.2 — ACI 318 Chapter 17 CCD Shear Lug Breakout Reference (Sec. 17.7.2 & 17.11.3)**:
   $$A_{Vco} = 4.5 c_{a1}^2, \quad A_{Vc} = (b_{col} + 3 c_{a1})(c_{top} + 1.5 c_{a1}), \quad V_b = 9 \lambda_a \sqrt{f'_m} c_{a1}^{1.5}, \quad V_{all,CCD} = \frac{0.70 (A_{Vc}/A_{Vco}) \psi_{ed,V} V_b}{1.5}$$
3. **Mechanism 4.3 — Out-of-Plane One-Way Shear of Grouted Bond Beam (TMS 402 Sec. 8.3.5.1.2)**:
   - Each side of the bond beam (height $b_{bb}$, effective depth $d_{bb}$) carries $V_{oop} = C_1 / 2$ to the adjacent vertical wall jamb bars:
     $$f_{v,oop} = \frac{C_1}{2 \cdot b_{bb} \cdot d_{bb}} \le F_{vm,oop} = 1.0 \sqrt{f'_m}$$
4. **Mechanism 4.4 — Anchor Reinforcement / Confining U-Bars When Breakout Governs (ACI 318 Sec. 17.5.2.1 & ACI 315 Sec. 2.8.3)**:
   - In thin $8"$ CMU walls where $C_1 > B_{ab,oop}$, detail **welded ASTM A706 Gr. 60 U-bars / hairpins** ($A_{s,hp} \ge C_1 / 32.0\text{ ksi}$) welded to the HSS webs that physically **hook around and enclose the vertical CMU jamb bars** in the adjacent cells outside the breakout cone.

### Step 5: Global CMU Wall Flexure & Axial Interaction Below Embedment (TMS 402 Sec. 8.3.4)
- Over effective width $b_{eff} = \min(6 t_{wall}, s_{col}, L_{wall})$, check $M_{wall} = M_a + V_a L_e$ and $P_{wall} = P_a + W_{wall}$ using cracked elastic $k, j$:
  $$f_b = \frac{2 M_{wall}}{b_{eff} d^2 j k} \le 0.45 f'_m, \qquad f_s = \frac{M_{wall}}{A_s j d} \le 32,000\text{ psi}, \qquad \frac{f_a}{F_a} + \frac{f_b}{F_b} \le 1.00$$

---

## 5. Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Criterion |
| :--- | :--- | :--- | :--- |
| **1** | **HSS Cantilever Post** | AISC 360 Ch. E–H ($K = 2.1$) | $P_a/P_{all} + M_a/M_{all} \le 1.00$; $V_a \le V_{all}$ |
| **2** | **Lateral Grout Bearing ($C_1, C_2$)** | TMS 402 Sec. 8.1.4.1 & 8.1.2 | $f_{b,lat} = V_a/(b L'_e) + 6 M'_a/(b L'^2_e) \le 0.25 f'_m$ |
| **3** | **End Cap Plate / Uplift Dowels** | TMS 402 Sec. 8.1.4.1; AISC Sec. J8 | $f_{br,vert} \le 0.25 f'_m$; $A_{s,uplift} \ge |P_a|/32\text{ ksi}$ |
| **4** | **Welded Rebar & Flare-Bevel Weld** | AISC Table J2.2; AWS D1.4 | ASTM A706 Gr. 60; $l_w \ge T_{bar}/(n_{sides} \cdot 3.281 d_b)$ |
| **5** | **Out-of-Plane Breakout & Hairpins** | TMS 402 Eq. 8-2/8-7; ACI 318 Sec. 17.5.2.1 | $B_{ab,oop} \ge C_1$ OR provide U-bars enclosing jamb bars ($A_{s,hp} \ge C_1/32\text{ ksi}$); $f_{v,oop} \le 1.0\sqrt{f'_m}$ |
| **6** | **Global CMU Wall Interaction** | TMS 402 Sec. 8.3.4 | $f_b \le 0.45 f'_m$, $f_s \le 32\text{ ksi}$, $f_a/F_a + f_b/F_b \le 1.00$ |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **ASTM A706 Grade 60 Mandate for Welded Rebar**: Always specify `ASTM A706 Grade 60` for all horizontal bond beam bars, vertical dowels, and U-bar hairpins welded to the steel post.
2. **Unpainted Steel Surface in Embedment Zone**: Call out on drawings: *"Embedded portion of HSS post and cap plate shall be clean and free of paint/primer per ACI 318 Sec. 26.5.6.1(d)."*
3. **Enclose Vertical Jamb Bars (ACI 315 Sec. 2.8.3)**: Welded U-bars/hairpins must physically wrap around the vertical CMU jamb bars in the cells immediately adjacent to the embedded post.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)
Design an embedded **`HSS4x4x1/4` ASTM A500 Gr. C cantilever post** ($H_{HSS}=4", B_{HSS}=4", t_{des}=0.233", Z=4.90\text{ in.}^3, F_y=50\text{ ksi}$) projecting $H = 4.0\text{ ft}$ ($48\text{ in.}$) above an **8-inch grouted CMU wall** ($t = 7.625", f'_m = 2,000\text{ psi}$) and embedded $L_e = 24.0\text{ in.}$:
- **Applied Out-of-Plane ASD Loads**: $V_a = 1.20\text{ kips}$ ($1,200\text{ lbs}$), $P_a = 1.50\text{ kips}$ ($e = 0$).
1. **Demands at Top of Wall**: $M_a = 1.20 \times 48 = 57.6\text{ kip-in.}$
2. **HSS Post Check**: $M_{all} = 50 \times 4.90 / 1.67 = 146.7\text{ kip-in.} \ge 57.6\text{ kip-in.}$ ($D/C = 0.393$) $\implies \textbf{OK}$.
3. **Lateral Grout Bearing & Couple Forces ($a_0 = 2.0" \implies L'_e = 22.0", M'_a = 57.6 + 1.2(2.0) = 60.0\text{ kip-in.}$)**:
   $$f_{b,lat} = \frac{1,200}{4.0 \times 22.0} + \frac{6(60,000)}{4.0 \times 22.0^2} = 13.6 + 186.0 = 199.6\text{ psi} \le 0.25(2,000) = 500\text{ psi} \implies \textbf{OK}$$
   - Discrete rebar couple ($d_{top} = 4.0"$, bottom bar at $20.0" \implies z_b = 16.0"$):
     $$C_1 = \frac{57.6 + 1.20(4.0 + 16.0)}{16.0} = 5.10\text{ kips} \; (5,100\text{ lbs}), \qquad C_2 = 5.10 - 1.20 = 3.90\text{ kips}$$
4. **Welded Horizontal U-Bar / Hairpin & Flare-Bevel Weld**:
   - Required area: $A_{s,req} = 5.10 / 32.0 = 0.159\text{ in.}^2 \implies$ Use **(1) `#4` ASTM A706 Gr. 60 U-bar** ($2$ legs $\times 0.20 = 0.40\text{ in.}^2$, one leg welded to each side of HSS).
   - Flare-bevel weld per leg ($d_b = 0.50"$, single side $n_{sides} = 1$):
     $$q_{w,all} = 3.281 \times 0.50 = 1.641\text{ kips/in.} \implies l_{w,req} = \frac{5.10 / 2}{1.641} = 1.55\text{ in.} \implies \textbf{Use } 2.5"\text{ flare-bevel weld per leg.}$$
5. **Out-of-Plane Breakout & One-Way Bond Beam Shear**:
   - Centered bar $l_b = 3.81"$, $c_{top} = 4.0" \implies A_{pt} = (4.0 + 2 \times 3.81)(3.81 + 3.81) = 88.5\text{ in.}^2$:
     $$B_{ab,oop} = 1.25 \times 88.5 \times \sqrt{2,000} = 4,947\text{ lbs} < C_1 = 5,100\text{ lbs} \quad (\text{Breakout governed!})$$
   - Because $C_1 = 5,100\text{ lbs} > B_{ab,oop} = 4,947\text{ lbs}$, detail the **`#4` ASTM A706 Gr. 60 U-bar hairpin** to **hook around the vertical `#5` CMU jamb bars** in the adjacent grouted cells ($12"$ on each side of the HSS post) per ACI 318 Sec. 17.5.2.1!
   - One-way bond beam shear ($b_{bb} = 8.0", d_{bb} = 5.25"$ at jamb bar):
     $$f_{v,oop} = \frac{5,100}{2 \times 8.0 \times 5.25} = 60.7\text{ psi} > 1.0\sqrt{2,000} = 44.7\text{ psi} \implies \textbf{Grout top 2 courses ($b_{bb} = 16.0"$): } f_{v,oop} = 30.4\text{ psi} \le 44.7\text{ psi} \implies \textbf{OK!}$$
