# End-to-End Calculation Procedure: Deck Guardrail Post-to-Framing & Post-to-Concrete Slab Sub-Assembly Synthesis

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Structural Sub-Assembly**: Exterior or interior guardrail system of height $H_{\text{guard}}$ ($36\text{ in.}$ residential R-3 internal / IRC or $42\text{ in.}$ commercial / California exterior deck) with posts spaced at $S_{\text{post}}$ ($4.0\text{ ft}$ to $6.0\text{ ft}$ o.c.), evaluated across two primary engineering assemblies:
  - **Assembly A (Wood Guardrail Post to Wood Deck Rim Joist / Blocking)**: $4\times 4$ or $6\times 6$ DF-L #1/#2 post mounted to the inside or outside of a wood rim joist ($2\times 10$ or $2\times 12$) using an upper tension tie ([Simpson DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2) or `HDU2-SDS2.5`) anchored into the deck joist/blocking and a lower through-bolt/compression blocking zone.
  - **Assembly B (Structural Steel HSS Post to Concrete Slab / Edge Curb)**: Cantilevered $\text{HSS}2.5\times 2.5\times 1/4$, $\text{HSS}3\times 3\times 1/4$, or $\text{HSS}4\times 4\times 1/4$ (ASTM A500 Gr. C) post CJP/fillet-welded to a steel base plate anchored to a concrete deck slab or perimeter curb via post-installed screw/adhesive anchors ([Simpson Titen HD](https://www.strongtie.com/screwanchors_mechanicalanchoringproducts/thd_anchor/p/titen-hd) or [SET-3G Epoxy](https://www.strongtie.com/epoxyanchoringadhesives_adhesives/set-3g_adhesive/p/set-3g)) or cast-in headed bolts.

### 1.2 Governing Codes & Standards
- **Building Code**: [2024 IBC Section 1607.9 (Handrails and Guards), Section 1015 (Guard Geometry), and Section 2407 (Glass Handrails and Guards)](https://www.pdhlibrary.com/sites/default/files/1416.0-2026%20Advanced%20Building%20Code%209th%20Edition%20-%20Structural%20-%20Significant%20Code%20Changes.pdf)
- **Load Standard**: [ASCE/SEI 7-22 Section 4.5.1 (Loads on Handrail and Guard Systems) and Chapter 30 (Exterior Wind)](https://www.engineeringexpress.com/wiki/whats-different-about-designing-for-a-mechanical-area-railing/)
- **Material & Connection Standards**: AWC NDS 2024 & DCA 6 (Prescriptive Residential Wood Deck Construction Guide), ANSI/AISC 360-22 & Design Guide 1, ACI 318-19/25 Chapter 17
- **Required Repository Database Tables**:
  - `database/ibc_cbc/v2024_ibc_v2025_cbc/IBC-2024_Section_1607.9_Guardrail_Loads.csv`
  - `database/nds_wood/v2024/NDS-2024_Table_12E_Bolts_Single_Shear.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv`
  - `database/aci_318_tms_402/aci_318_19/ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv`

### 1.3 Complete Load Path & Force Transfer Mechanism
1. **Top Rail & Infill Pickets/Glass**: Concentrated live load ($P_{\text{conc}} = 200\text{ lbs}$), uniform live load ($w_{\text{unif}} = 50\text{ plf}$), or exterior C&C wind pressure transfers from the top rail/infill into the cantilevered guardrail post.
2. **Cantilevered Post Flexure**: The post acts as a vertical cantilever of lever arm $L_{\text{arm}} = H_{\text{guard}} + e_{\text{base}}$, developing maximum moment $M_{\text{post}}$ and horizontal shear $V_{\text{post}}$ at the deck attachment.
3. **Assembly A (Wood Post-to-Framing Force Couple)**:
   - Notching a $4\times 4$ post reduces net section by $50\%$ and is prohibited under DCA 6 / modern plan check practice; furthermore, relying on two through-bolts into a single $2\times$ rim joist induces forbidden **cross-grain tension/bending** in the rim joist (NDS Sec. 11.1.2).
   - Instead, $M_{\text{post}}$ resolves into an upper horizontal tension force $T_{\text{top}}$ transferred directly into a perpendicular floor joist/blocking via a [Simpson DTT2Z Deck Tension Tie](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2) and a lower compression bearing force $C_{\text{bot}}$ separated by vertical lever arm $d_{\text{couple}}$.
4. **Assembly B (Steel Post-to-Concrete Slab Anchorage)**:
   - $M_{\text{post}}$ resolves into tension in the windward anchor bolts ($T_{\text{bolt}}$) and compression bearing under the leeward edge of the steel base plate, transferred into the concrete slab/curb and checked for **close-edge concrete breakout** ($c_{a1}$ near slab edge) per ACI 318-19 Chapter 17.

---

## Section 2: Load Combinations & Internal Forces at the Critical Section

### 2.1 Governing Live & Wind Loads on Guardrail Post
Query `IBC-2024_Section_1607.9_Guardrail_Loads.csv` ([IBC Sec. 1607.9 / ASCE 7-22 Sec. 4.5.1](https://www.pdhlibrary.com/sites/default/files/1416.0-2026%20Advanced%20Building%20Code%209th%20Edition%20-%20Structural%20-%20Significant%20Code%20Changes.pdf)):
1. **Case 1 — Concentrated Top-Rail Live Load (All Occupancies)**:
   $$P_L = 200\text{ lbs} \quad (\text{applied horizontally outward/inward at } H_{\text{guard}})$$
2. **Case 2 — Uniform Top-Rail Live Load (Commercial / Multi-Family Public Areas, Non-Concurrent with Case 1)**:
   $$V_{L,\text{unif}} = w_{\text{unif}} \cdot S_{\text{post}} = (50\text{ plf}) \cdot S_{\text{post}} \quad (\text{lbs})$$
3. **Case 3 — Exterior Component & Cladding Wind Load (Solid / Glass / High-Solidity Guards)**:
   $$V_W = p_W \cdot H_{\text{guard}} \cdot S_{\text{post}} \quad (\text{acting at } H_{\text{guard}} / 2)$$
4. **Structural Glass Baluster / Infill Safety Factor (IBC Section 2407.1)**:
   If structural glass panels support the top rail without redundant metal posts, multiply live load demands on glass and base shoe clamps by $\text{FS}_{\text{glass}} = 4.0$.

### 2.2 Factored Post Base Shear & Moment (LRFD & ASD)
Let $H_{\text{eff}} = H_{\text{guard}} + e_{\text{fas}}$ (in.), where $e_{\text{fas}}$ is the distance from walking surface to center of rim-joist connection ($e_{\text{fas}} = 0$ for surface-mounted concrete base plate):
- **ASD Unfactored Demands ($1.0 L$ or $0.6 W$)**:
  $$V_a = \max\left(200\text{ lbs},\; 50 S_{\text{post}},\; 0.6 V_W\right)$$
  $$M_a = \max\left(200 \cdot H_{\text{eff}},\; (50 S_{\text{post}}) \cdot H_{\text{eff}},\; 0.6 V_W \cdot \left(\frac{H_{\text{guard}}}{2} + e_{\text{fas}}\right)\right) \quad (\text{lb-in.})$$
- **LRFD Factored Demands ($1.6 L$ or $1.0 W$)**:
  $$V_u = \max\left(1.6(200) = 320\text{ lbs},\; 1.6(50 S_{\text{post}}),\; 1.0 V_W\right)$$
  $$M_u = \max\left(320 \cdot H_{\text{eff}},\; 80 S_{\text{post}} \cdot H_{\text{eff}},\; 1.0 V_W \cdot \left(\frac{H_{\text{guard}}}{2} + e_{\text{fas}}\right)\right) \quad (\text{lb-in.})$$
*(Example: For a $42\text{ in.}$ residential/commercial guard with $e_{\text{fas}} = 4.5\text{ in.}$ and $P_L = 200\text{ lbs}$: $M_a = 200 \times 46.5 = 9,300\text{ lb-in.} = 775\text{ lb-ft}$; $M_u = 1.6 \times 9,300 = 14,880\text{ lb-in.} = 1,240\text{ lb-ft}$).*

---

## Section 3: Primary Member Verification (Top Rail & Cantilevered Post)

### 3.1 Top Rail Bending & Shear Over Span $S_{\text{post}}$
$$M_{\text{rail},a} = \max\left(\frac{200 \cdot (12 S_{\text{post}})}{4},\; \frac{(50/12) \cdot (12 S_{\text{post}})^2}{8}\right) \le F'_b S_{x,\text{rail}} \;(\text{Wood}) \quad \text{or} \quad \frac{M_n}{\Omega_b} \;(\text{Steel})$$

### 3.2 Cantilevered Guardrail Post Flexure, Shear & Deflection
1. **Wood Post ($4\times 4$: $b = 3.5\text{ in.}, d = 3.5\text{ in.}, S_x = 7.146\text{ in.}^3, I_x = 12.51\text{ in.}^4$ or $6\times 6$: $S_x = 27.73\text{ in.}^3$)**:
   Using full un-notched cross section and conservative load duration factor $C_D = 1.00$ for live occupancy impact (or $C_D = 1.60$ where permitted for short-term impact):
   $$f_b = \frac{M_a}{S_x} \le F'_b = F_b C_D C_M C_t C_F, \qquad f_v = \frac{1.5 V_a}{b d} \le F'_v$$
   *(Note: For a $4\times 4$ DF-L #2 post with $F_b = 900\text{ psi}, C_F = 1.5 \implies F'_b = 1,350\text{ psi}$ at $C_D=1.0$: $M_{\text{allow}} = 1,350 \times 7.146 = 9,647\text{ lb-in.} \ge 9,300\text{ lb-in.}$ OK without notching!).*
2. **Steel HSS Post (e.g., $\text{HSS}2.5\times 2.5\times 1/4$ or $\text{HSS}3\times 3\times 1/4$, ASTM A500 Gr. C, $F_y = 50\text{ ksi}$)**:
   $$\phi_b M_n = 0.90 F_y Z_x \ge M_u \quad (\text{LRFD}), \qquad \frac{M_n}{\Omega_b} = \frac{F_y Z_x}{1.67} \ge M_a \quad (\text{ASD})$$
3. **Top-of-Post Serviceability Deflection**:
   $$\Delta_{\text{top}} = \frac{P_L H_{\text{eff}}^3}{3 E I_x} + \theta_{\text{base}} H_{\text{eff}} \le \frac{H_{\text{guard}}}{60}\text{ to }\frac{H_{\text{guard}}}{120}$$

---

## Section 4: Sequential Connection Limit States Along the Load Path

### Step 4.1: Assembly A — Wood Post-to-Deck Framing Connection (DCA 6 / Simpson `DTT2Z`)
Let the upper tension bolt (`DTT2Z` anchor bolt) be located $d_1$ above the bottom of the rim joist and the lower bolt/compression bearing center be located $d_2$ above the bottom, giving internal moment arm $d_{\text{couple}} = d_1 - d_2$ (for a $2\times 10$ or $2\times 12$ rim joist, typically $d_{\text{couple}} = 6.5\text{ in. to }8.0\text{ in.}$):
1. **Upper Tension Tie Force ($T_{\text{top}}$)**:
   Taking moments about the lower compression bearing point (with top rail load $V_a$ at height $H_{\text{top}}$ above the lower bolt):
   $$T_{\text{top},a} = \frac{V_a \cdot H_{\text{top}}}{d_{\text{couple}}}$$
   *(Example: $V_a = 200\text{ lbs}$, $H_{\text{top}} = 42 + 7.5 = 49.5\text{ in.}$, $d_{\text{couple}} = 6.5\text{ in.} \implies T_{\text{top},a} = 200 \times 49.5 / 6.5 = 1,523\text{ lbs}$).*
2. **Simpson Tension Tie Capacity Verification**:
   Query `Simpson_C-C-2026_Holdowns_HDU_HDUE_DTT.csv` ([Simpson DTT2Z](https://www.strongtie.com/decks_decksandfences/dtt2_tie/p/dtt2)):
   - `DTT2Z` with (8) $1/4\text{ in.} \times 1\text{-}1/2\text{ in.}$ SDS screws into wide face of floor joist/blocking:
     $$T_{\text{allow,DTT2Z}} = 1,825\text{ lbs } (C_D = 1.60) / 1,500\text{ lbs IRC Lateral Rating} \quad \text{or use } \text{HDU2-SDS2.5 } (T_{\text{allow}} = 3,075\text{ lbs})$$
3. **Bolt Shear in Post for Vertical Gravity / In-Plane Load (NDS Table 12E)**:
   Query `NDS-2024_Table_12E_Bolts_Single_Shear.csv` for $1/2\text{ in.}$ through-bolts and verify edge/end distances ($l_{\text{end}} \ge 7 D = 3.5\text{ in.}$, $l_{\text{edge}} \ge 1.5 D$).

### Step 4.2: Assembly B — Steel HSS Post Base Plate & Weld Verification (AISC 360 & DG1)
For a square steel base plate ($B_p \times N_p \times t_p$, ASTM A36) with 4 corner anchors at spacing $g \times s_b$ ($d_{\text{anchor}}$ from compression edge):
1. **Post-to-Base Plate Weld Check (AISC Sec. J2.4)**:
   For all-around fillet weld (leg size $w$, perimeter $L_w = 4 B_{\text{HSS}}$, elastic section modulus $S_w = B_{\text{HSS}}^2 + B_{\text{HSS}}^2 / 3 = \frac{4}{3} B_{\text{HSS}}^2$):
   $$f_w = \sqrt{\left(\frac{M_u}{S_w}\right)^2 + \left(\frac{V_u}{L_w}\right)^2} \le 1.392 D \text{ kips/in. (LRFD)}$$
2. **Anchor Tension Group Force & Base Plate Thickness ($t_{p,\text{req}}$)**:
   With lever arm $z_{\text{arm}} \approx d_{\text{anchor}} - \frac{a_{\text{bearing}}}{2}$ between tension anchors and compression edge of the HSS/plate:
   $$T_{u,\text{group}} = \frac{M_u}{z_{\text{arm}}} \implies T_{u,\text{bolt}} = \frac{T_{u,\text{group}}}{n_{\text{tension bolts}}}$$
   $$t_{p,\text{req}} = \sqrt{\frac{4 (T_{u,\text{group}} \cdot b_{\text{cant}})}{0.90 F_y B_p}} \quad (\text{typically } 1/2\text{ in. to }3/4\text{ in. plate})$$

### Step 4.3: Concrete Slab / Edge Curb Anchorage Check (ACI 318-19 Chapter 17)
Query `ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv` and `Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv` ([Simpson Titen HD](https://www.strongtie.com/screwanchors_mechanicalanchoringproducts/thd_anchor/p/titen-hd) / [SET-3G](https://www.strongtie.com/epoxyanchoringadhesives_adhesives/set-3g_adhesive/p/set-3g)):
1. **Close-Edge Concrete Breakout in Tension ($\phi N_{cbg}$ per ACI 318-19 Sec. 17.6.2)**:
   Because guardrail base plates are mounted near the slab edge ($c_{a1}$ often $2.5\text{ in. to }4.0\text{ in.} < 1.5 h_{\text{ef}}$), apply the edge disturbance factor $\psi_{ed,N} = 0.7 + 0.3\left(\frac{c_{a,\min}}{1.5 h_{\text{ef}}}\right)$ and projected area $A_{Nc}$ truncated by the slab edge:
   $$\phi N_{cbg} = \phi \frac{A_{Nc}}{A_{Nc0}} \psi_{ec,N} \psi_{ed,N} \psi_{c,N} \psi_{cp,N} N_b \ge T_{u,\text{group}}$$
2. **Concrete Edge Breakout in Shear Toward Slab Edge ($\phi V_{cbg}$ per ACI 318-19 Sec. 17.7.2)**:
   For outward guardrail push toward the free slab edge ($c_{a1}$), verify $\phi V_{cbg}$ (including thin-slab modification $\psi_{h,V} = \sqrt{1.5 c_{a1} / h_a}$ when slab thickness $h_a < 1.5 c_{a1}$) OR transfer shear via supplemental anchor hairpin reinforcement ($\text{#4}$ U-bars enclosing slab edge bars per ACI 318 Sec. 17.5.2.1).
3. **Combined Tension and Shear Interaction (ACI 318-19 Sec. 17.8)**:
   $$\left(\frac{N_{ua}}{\phi N_n}\right)^{5/3} + \left(\frac{V_{ua}}{\phi V_n}\right)^{5/3} \le 1.0$$

---

## Section 5: Supporting Deck Rim Joist / Concrete Slab Edge Verification
- **Wood Deck Framing**: Verify that the perpendicular floor joist receiving the `DTT2Z` tension tie is continuous or blocked across at least two joist bays with $16\text{d}$ nails/framing angles to distribute the $1,500+\text{ lb}$ horizontal force into the deck diaphragm without pulling the rim joist away from the joist ends.
- **Concrete Slab / Curb Cantilever**: Verify that the concrete slab edge or curb has sufficient negative/top flexural reinforcement ($A_s$ per ft width) to resist the concentrated guardrail base moment $M_u / s_{\text{eff}}$:
  $$\phi M_{n,\text{slab}} = 0.90 A_s f_y \left(d - \frac{a}{2}\right) \ge \frac{M_u}{B_p + 2 h_{\text{slab}}}$$

---

## Section 6: Mandatory Detailing & Construction Notes
- **Zero Post Notching**: Guardrail $4\times 4$ wood posts shall NEVER be notched at the rim joist connection; keep the full $3.5\text{ in.} \times 3.5\text{ in.}$ cross section continuous.
- **Full-Depth Solid Blocking at Every Post**: Install full-depth $2\times$ solid blocking between deck joists at every guardrail post location fastened with Simpson `A35` / `L70` angles or (4) $16\text{d}$ toe-nails/screws to prevent rim joist torsional rolling.
- **Minimum Concrete Edge Distance ($c_{a1}$)**: Maintain minimum edge distance $c_{\min}$ per `Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv` ($1.75\text{ in.}$ for $3/8\text{ in.} / 1/2\text{ in.}$ `Titen HD` or `SET-3G`) to prevent installation splitting.

---

## Section 7: Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :--- | :--- | :--- | :--- |
| **1** | Guardrail Live & Wind Loads | 2024 IBC Sec. 1607.9 & ASCE 7-22 Sec. 4.5.1 | $P_{\text{conc}} = 200\text{ lbs}$ or $w_{\text{unif}} = 50\text{ plf}$ (non-concurrent) |
| **2** | Glass Guard Safety Factor (if applicable) | 2024 IBC, Sec. 2407.1 | $\text{FS}_{\text{glass}} = 4.0$ on structural glass & base shoe |
| **3.1** | Top Rail Flexure & Infill Check | NDS 2024 Ch. 3 / AISC 360 Ch. F | $M_{\text{rail}} \le M_{\text{allow}}$; $P_{\text{infill}} = 50\text{ lbs}$ over $1\text{ ft}^2$ |
| **3.2** | Cantilever Post Flexure & Deflection | NDS Sec. 3.3 / AISC Sec. F7 & IBC 1604.3 | $M_a \le F'_b S_x$ (un-notched) or $M_u \le \phi_b M_n$ |
| **4.1** | Wood Post Tension-Compression Couple | DCA 6 & Simpson `DTT2Z` / `HDU2` | $T_{\text{top}} = V_a H_{\text{top}} / d_{\text{couple}} \le T_{\text{allow,DTT2Z/HDU}}$ |
| **4.2** | Steel Post Weld & Base Plate Bending | AISC 360 Sec. J2.4 & Design Guide 1 | $f_w \le 1.392 D$; $t_p \ge \sqrt{4 M_{u,p} / (0.90 F_y B_p)}$ |
| **4.3** | Concrete Slab Edge Breakout & Interaction | ACI 318-19, Sec. 17.6.2, 17.7.2 & 17.8 | $(N_{ua}/\phi N_{cbg})^{5/3} + (V_{ua}/\phi V_{cbg})^{5/3} \le 1.0$ |
| **5** | Deck Rim Blocking / Slab Edge Flexure | NDS Sec. 11.1.2 & ACI 318 Ch. 7/9 | Zero cross-grain tension; $\phi M_{n,\text{slab}} \ge M_u / b_{\text{eff}}$ |
