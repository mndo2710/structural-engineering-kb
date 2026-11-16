# End-to-End Calculation Procedure: Wall-Mounted Cantilever & Diagonal Tie-Back Awning / Canopy Sub-Assembly Synthesis

## Section 1: Design Assumptions, Load Path & Governing Codes

### 1.1 System & Connection Configuration
- **Structural Sub-Assembly**: Wall-mounted exterior architectural awning or entry canopy projecting a horizontal span $L_c$ from a primary building wall at height $h_c$ above ground, configured as either:
  - **Configuration A (Pure Cantilever Outlooker Awning)**: Structural steel HSS outlooker beams (e.g., $\text{HSS}6\times 3\times 1/4$, ASTM A500 Gr. C) welded to a vertical wall mounting plate anchored to a reinforced concrete/CMU wall or structural steel/wood column at spacing $S_b$ ([SkyCiv Steel Connection Documentation](https://skyciv.com/docs/)).
  - **Configuration B (Diagonal Tie-Back Rod Canopy)**: Horizontal steel HSS/channel outlooker beam pinned at the lower wall bracket and supported near its outer tip (at distance $L_{\text{rod}}$ from the wall) by an inclined steel clevis tie-back rod (angle $\theta$ from horizontal, vertical drop $H_{\text{rod}} = L_{\text{rod}} \tan\theta$) anchored to an upper wall bracket.

### 1.2 Governing Codes & Standards
- **Building Code**: [2024 IBC / 2025 CBC Section 1607.13.2 & Section 3105 (Awnings and Canopies)](https://codes.iccsafe.org/content/WABellevueBC2021P1/chapter-16-structural-design)
- **Wind & Seismic Loads**: [ASCE/SEI 7-22 Section 30.11 (Attached Canopies on Walls, Figures 30.11-1A & 30.11-1B) and Section 13.3.1 / Table 13.5-1 (Appendages and Ornamentations)](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)
- **Material & Anchorage Standards**: ANSI/AISC 360-22 (Steel Members, Rods, Pins, Bolts & Welds), ACI 318-19/25 Chapter 17 (Concrete Anchorage), TMS 402-22 (Masonry Anchorage), AWC NDS 2024 (Wood Wall Lag Screw/SDS Anchorage)
- **Required Repository Database Tables**:
  - `database/asce_7/v7_22/ASCE7-22_Figure_30.11-1A_1B.csv`
  - `database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv`
  - `database/aisc_360/ch_j_connections/AISC360-22_Table_J2.5_Welded_Joints.csv` & `AISC360-22_Table_J3.2_Bolt_Strength.csv`
  - `database/aci_318_tms_402/aci_318_19/ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv`

### 1.3 Complete Load Path & Force Transfer Mechanism
1. **Surface Decking / Louvers to Purline/Joists**: Gravity dead/live/snow loads and C&C wind pressures (separate upper/lower surface $GC_p$ per Figure 30.11-1A) transfer from decking to secondary purlins.
2. **Primary Outlooker Beam**: Purlins transfer net combined downward or upward wind pressure ($GC_p$ per Figure 30.11-1B) and gravity loads into the outlooker beam at spacing $S_b$:
   - In **Configuration A (Cantilever)**: The outlooker transfers vertical shear $V_{\text{wall}}$ and full overturning moment $M_{\text{wall}} = w \cdot L_c^2 / 2$ to the wall mounting plate.
   - In **Configuration B (Tie-Back Rod)**: Vertical tip reaction $R_{\text{tip}}$ resolves into axial force in the diagonal rod ($P_{\text{rod}} = R_{\text{tip}} / \sin\theta$: tension under downward load, compression/buckling under net wind uplift!) and horizontal axial force in the outlooker beam ($P_{\text{beam}} = R_{\text{tip}} / \tan\theta$).
3. **Wall Bracket & Substrate Anchorage**: The upper and lower brackets transfer tension ($T_{\text{bracket}}$) and vertical shear ($V_{\text{bracket}}$) through weld groups and anchor bolts into the supporting concrete, CMU, steel, or wood stud wall.

---

## Section 2: Load Combinations & Internal Forces at the Critical Section

### 2.1 Attached Canopy Wind Pressures (ASCE 7-22 Section 30.11)
Query `ASCE7-22_Figure_30.11-1A_1B.csv` using height ratio $h_c / h_e$ and effective wind area $A = L_c \cdot S_b$:
$$p_{\text{down}} = q_h K_d (GC_{p,\text{pos,net}}) \quad (\text{psf}), \qquad p_{\text{up}} = q_h K_d (GC_{p,\text{neg,net}}) \quad (\text{psf})$$
where $K_d = 0.85$ and $GC_{p,\text{net}}$ is taken from Figure 30.11-1B (typically $+0.60\text{ to }+1.40$ downward and $-0.70\text{ to }-2.40$ upward uplift).

### 2.2 Seismic Appendage Force (ASCE 7-22 Table 13.5-1)
From `ASCE7-22_Table_13.5-1.csv` for *Appendages and Ornamentations*: $C_{AR} = 2.2$ (above grade), $R_{po} = 1.5$, $\Omega_{0p} = 1.75$:
$$F_{p,E} = \max\left(0.4 S_{DS} I_p W_p \frac{H_f}{R_\mu} \frac{2.2}{1.5},\; 0.3 S_{DS} I_p W_p\right) \le 1.6 S_{DS} I_p W_p, \qquad E_v = \pm 0.2 S_{DS} W_p$$

### 2.3 Internal Demands for Configuration A (Cantilever Span $L_c$) vs. Configuration B (Tie-Back at $L_{\text{rod}}$)
Let $w_{\text{down}}$ and $w_{\text{up}}$ (lb/ft) be the factored (LRFD or ASD) net downward and net upward linear loads along the outlooker beam ($w = p \cdot S_b$):
1. **Configuration A (Pure Cantilever)**:
   $$V_{\text{wall}} = w \cdot L_c, \qquad M_{\text{wall}} = \frac{w \cdot L_c^2}{2}$$
2. **Configuration B (Diagonal Tie-Back Rod at $L_{\text{rod}}$ with Overhang $L_{\text{ovh}} = L_c - L_{\text{rod}}$)**:
   - Vertical reaction at rod attachment:
     $$R_{\text{tip}} = \frac{w \cdot L_c^2}{2 L_{\text{rod}}}$$
   - Diagonal rod axial force (Tension $+$ under downward load; Compression $-$ under net wind uplift $0.9D + 1.0W_{\text{up}}$ or $0.6D + 0.6W_{\text{up}}$):
     $$P_{\text{rod}} = \frac{R_{\text{tip}}}{\sin\theta} = \frac{w \cdot L_c^2}{2 L_{\text{rod}} \sin\theta}$$
   - Outlooker beam axial force and maximum internal bending moment:
     $$P_{\text{beam}} = \frac{R_{\text{tip}}}{\tan\theta}, \qquad M_{\text{beam,max}} = \max\left(\frac{w L_{\text{ovh}}^2}{2},\; \frac{R_{\text{tip}}^2}{2 w} - R_{\text{tip}} L_{\text{ovh}}\right)$$
   - Upper tie-back wall bracket demands:
     $$T_{\text{upper}} = P_{\text{rod}} \cos\theta = \frac{R_{\text{tip}}}{\tan\theta}, \qquad V_{\text{upper}} = P_{\text{rod}} \sin\theta = R_{\text{tip}}$$
   - Lower beam wall bracket demands:
     $$C_{\text{lower}} = P_{\text{rod}} \cos\theta \;(\text{or Tension under uplift}), \qquad V_{\text{lower}} = w L_c - R_{\text{tip}}$$

---

## Section 3: Primary Member Verification (AISC 360-22)

### 3.1 Outlooker Beam Combined Axial + Flexural Check (AISC 360 Chapter H)
Evaluate flexural strength ($\phi_b M_n$ or $M_n/\Omega_b$ per Ch. F) and axial compressive/tensile strength ($\phi_c P_n$ or $P_n/\Omega_c$ per Ch. D/E) and verify interaction per [AISC 360-22 Equations H1-1a and H1-1b](https://skyciv.com/docs/):
- For $\frac{P_r}{P_c} \ge 0.2$:
  $$\frac{P_r}{P_c} + \frac{8}{9}\left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right) \le 1.0$$
- For $\frac{P_r}{P_c} < 0.2$:
  $$\frac{P_r}{2 P_c} + \left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right) \le 1.0$$

### 3.2 Diagonal Tie-Back Rod Tension & Uplift Compression Check (AISC 360 Chapters D & E)
1. **Threaded Rod / Clevis Tension under Downward Load (AISC Sec. J3.6 / Table J3.2)**:
   $$R_n = F_{nt} A_b = (0.75 F_u) \left(\frac{\pi d_{\text{rod}}^2}{4}\right), \qquad \phi R_n = 0.75 R_n \ge T_{u,\text{rod}}, \qquad \frac{R_n}{\Omega} = \frac{R_n}{2.00} \ge T_{a,\text{rod}}$$
2. **Critical Wind Uplift Reversal Check ($0.9D + 1.0W_{\text{up}}$ / $0.6D + 0.6W_{\text{up}}$)**:
   - Under net upward wind pressure ($p_{\text{up}}$), if $w_{\text{up}} > w_D$, the diagonal rod goes into **compression**!
   - Either size the diagonal brace as a compression strut (HSS or Pipe satisfying $\frac{L_c}{r} \le 200$ and AISC Sec. E3 flexural buckling $P_c \ge C_{r,\text{rod}}$), OR design the outlooker beam and lower wall connection as a full moment cantilever capable of resisting net wind uplift alone with the slender rod slack ($P_{\text{rod,comp}} = 0$).

---

## Section 4: Sequential Connection Limit States Along the Load Path

### Step 4.1: Clevis Pin, Gusset Ear Plate & Fillet Weld Checks (AISC 360 Chapter J)
1. **Pin Shear & Bearing (AISC Sec. D5 & J7)**:
   $$\phi V_{n,\text{pin}} = 0.75 (0.6 F_{u,\text{pin}}) \left(2 \cdot \frac{\pi d_{\text{pin}}^2}{4}\right) \ge P_{u,\text{rod}}$$
2. **Gusset Plate Tension Yielding, Pin Tearout & Block Shear (AISC Sec. D5.1 & J4.3)**:
   $$\phi P_{n,\text{tearout}} = 0.75 \left(0.6 F_u \cdot 2 t_p b_{\text{eff}}\right) \ge P_{u,\text{rod}}$$
3. **Outlooker-to-Wall Plate Fillet Weld Group (AISC Sec. J2.4 & Table J2.5)**:
   Using weld polar/elastic section modulus $S_w$ and weld throat $t_e = 0.707 w$:
   $$f_{w,\text{max}} = \sqrt{\left(\frac{V}{L_w} \pm \frac{M_y}{S_{wy}}\right)^2 + \left(\frac{T}{L_w} + \frac{M_x}{S_{wx}}\right)^2} \le \phi R_{nw} = 1.392 D \text{ kips/in. (LRFD)} \quad \text{or} \quad 0.928 D \text{ kips/in. (ASD)}$$

### Step 4.2: Wall Mounting Plate Bending & Prying Action (AISC Design Guide 1 / Part 9)
For projection distance $b'$ from the HSS flange/gusset to the anchor bolt centerline:
$$M_{p,\text{plate}} = T_{\text{bolt}} \cdot b', \qquad t_{p,\text{req}} = \sqrt{\frac{4 M_{u,\text{plate}}}{0.90 F_y b_{\text{eff}}}} \;(\text{LRFD}) \quad \text{or} \quad \sqrt{\frac{6 M_{a,\text{plate}}}{0.60 F_y b_{\text{eff}}}} \;(\text{ASD})$$

### Step 4.3: Wall Substrate Anchorage (Concrete/CMU vs. Wood/Steel Studs)
- **Concrete / CMU Wall Substrate (ACI 318-19 Ch. 17 / TMS 402-22)**:
  Query `ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv` and `Simpson_C-A-2023_Titen_HD_SET3G_PAB_Anchors.csv` ([Simpson SET-3G ESR-4057](https://www.strongtie.com/epoxyanchoringadhesives_adhesives/set-3g_adhesive/p/set-3g)). Check steel strength, concrete/masonry breakout ($\phi N_{cb}, \phi V_{cb}$), adhesive bond ($\phi N_{ag}$), and combined tension-shear interaction:
  $$\left(\frac{N_{ua}}{\phi N_n}\right)^{5/3} + \left(\frac{V_{ua}}{\phi V_n}\right)^{5/3} \le 1.0$$
- **Wood Stud / Column Wall Substrate (NDS 2024 Chapter 12)**:
  For lag screws or Simpson `SDS` screws into structural wood columns/double studs: check withdrawal capacity ($W' = W C_D C_M C_t C_{eg} \cdot L_{\text{thread}}$), lateral shear capacity ($Z'$), and combined inclined load (Hankinson's formula per NDS Eq. 12.4-1).

---

## Section 5: Supporting Wall / Column Global Verification
- Verify that the supporting wall stud, steel column, or CMU pilaster resists the eccentric bracket moment $M_{\text{ecc}} = T_{\text{upper}} H_{\text{rod}}$ and out-of-plane point loads between floor and roof diaphragms:
  $$\frac{P_{\text{wall}}}{P_{c,\text{wall}}} + \frac{M_{\text{wall,wind}} + M_{\text{awning}}}{M_{c,\text{wall}}} \le 1.0$$

---

## Section 6: Mandatory Detailing & Construction Notes
- **Wind Uplift Reversal on Tie-Back Rods**: Clearly note on plans whether the diagonal tie-back member is a solid round rod (tension-only; requires bottom outlooker moment connection for wind uplift) or an HSS/Pipe compression strut.
- **Through-Bolting vs. Adhesive Anchors in Hollow CMU**: Post-installed expansion/screw anchors are prohibited in ungrouted hollow CMU cells for overhead/cantilever tension awnings; specify solid grouted bond beams/cells with Simpson `SET-3G` epoxy or threaded rod with screen tube per ICC-ES ESR.
- **Waterproofing & Backing Blocking**: Provide solid structural backing blocking or steel spreader channels behind exterior stucco/cladding at all bracket penetrations so clamping preload does not crush nonstructural finishes.

---

## Section 7: Summary Calculation & Detailing Checklist Table

| Step | Design Verification Item | Governing Code Reference | Limit State / Acceptance Equation |
| :--- | :--- | :--- | :--- |
| **1** | Canopy Net Wind Pressures ($p_{\text{down}}, p_{\text{up}}$) | ASCE 7-22, Sec. 30.11 (Fig. 30.11-1B) | $p = q_h K_d (GC_{p,\text{net}})$ for both downward $+$ and uplift $-$ |
| **2** | Seismic Appendage Force ($F_{p,E}$) | ASCE 7-22, Sec. 13.3.1 & Table 13.5-1 | $C_{AR} = 2.2,\; R_{po} = 1.5,\; \Omega_{0p} = 1.75$ |
| **3.1** | Outlooker Beam Axial + Flexure | AISC 360-22, Sec. H1.1 (Eq. H1-1a/b) | $\frac{P_r}{P_c} + \frac{8}{9}\left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right) \le 1.0$ |
| **3.2** | Diagonal Tie-Back Rod Tension & Uplift | AISC 360-22, Sec. D2, E3 & J3.6 | $T_r \le P_{c,\text{tension}}$; check compression buckling under $0.6D + 0.6W_{\text{up}}$ |
| **4.1** | Clevis Pin, Gusset Ear & Bracket Welds | AISC 360-22, Sec. D5, J2.4 & J4.3 | $f_{w,\text{max}} \le 1.392 D\text{ (LRFD)} / 0.928 D\text{ (ASD)}$ |
| **4.2** | Wall Mounting Plate Bending ($t_{p,\text{req}}$) | AISC Design Guide 1 / Manual Part 9 | $t_p \ge \sqrt{4 M_u / (0.90 F_y b_{\text{eff}})}$ |
| **4.3** | Wall Anchor Tension + Shear Interaction | ACI 318-19 Ch. 17 / TMS 402 / NDS Ch. 12 | $(N_{ua}/\phi N_n)^{5/3} + (V_{ua}/\phi V_n)^{5/3} \le 1.0$ |
| **5** | Supporting Wall Pilaster / Stud Check | NDS Sec. 3.9 / AISC Ch. H / TMS 402 | Combined axial + out-of-plane bending interaction $\le 1.0$ |
