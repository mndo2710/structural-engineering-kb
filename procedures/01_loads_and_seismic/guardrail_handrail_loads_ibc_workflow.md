# Calculation Procedure: Guardrail & Handrail Structural Load Analysis (2024 IBC / ASCE 7-22)

## 1. Code References & Database Dependencies

* **Primary Building Code**: [2024 IBC Section 1607.9 / 2025 CBC (Handrails and Guards)](https://titanap.com/blog/glass-railing-code-compliance-guide) and [IBC Section 1015 (Guards Geometric Requirements) & Section 2407 (Glass Handrails and Guards)](https://titanap.com/blog/glass-railing-code-compliance-guide)

* **Primary Load Standard**: [ASCE/SEI 7-22 Section 4.5.1 (Loads on Handrails and Guard Systems)](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784415788/part/provisions/standard-chapter/s4/standard-sec-ver/s4.5.1.1.ver.atom)

* **Load Combinations**: [ASCE/SEI 7-22 Chapter 2 (Sections 2.3.1 and 2.4.1)](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)

* **Required CSV Database Tables**:

  * `database/ibc_cbc/v2024_ibc_v2025_cbc/IBC-2024_Section_1607.9_Guardrail_Loads.csv`

  * `database/asce_7/v7_22/ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv`

  * `database/asce_7/v7_22/ASCE7-22_Figure_29.4-2.csv` (for open trellis/picket exterior wind check)

## 2. Input Parameters (`GuardrailLoadsInputDTO`)

| Parameter | Symbol | Units | Description / Typical Residential & Commercial Range | 
| ----- | ----- | ----- | ----- | 
| Occupancy Classification | $ext{Occ}$ | \- | `R-3_Residential` (1- & 2-family dwellings / within R-2 units), `Commercial_Standard`, or `Assembly_Bleachers` | 
| Guard Height Above Deck | $H_{	ext{guard}}$ | in. | Minimum $36	ext{ in.}$ (IRC / R-3 interior) or $42	ext{ in.}$ (Commercial / CBC exterior decks) | 
| Post Spacing On-Center | $S_{	ext{post}}$ | ft | Center-to-center spacing of guardrail posts (typically $4.0 - 6.0	ext{ ft}$) | 
| Post Attachment Offset | $e_{	ext{fas}}$ | in. | Vertical distance from deck surface down to center of fascia/rim-joist bolts (0 if surface-mounted top base plate) | 
| Infill System Type | $ext{Infill}$ | \- | `Open_Pickets_Cables`, `Solid_Panel`, or `Structural_Glass` | 
| Exterior Wind Pressure | $p_W$ | psf | Unfactored C&C wind pressure on exterior guard (if exposed to wind) | 
| Guard Self-Weight | $w_D$ | plf | Linear dead weight of rail, balusters/glass, and posts (typically $10 - 35	ext{ plf}$) | 

## 3. Step-by-Step Calculation Procedure

### Step 1: Code Live Load Determination (`IBC Section 1607.9` / `ASCE 7-22 Section 4.5.1`)

Query `IBC-2024_Section_1607.9_Guardrail_Loads.csv` based on Occupancy Classification ([ASCE 7-22 Section 4.5.1.1](https://amplify.asce.org/popup-data?apath=/asceworks/standard/9780784415788/part/provisions/standard-chapter/s4/standard-sec-ver/s4.5.1.1.ver.atom) & [IBC Glass/Guard Compliance Guide](https://titanap.com/blog/glass-railing-code-compliance-guide)):

1. **Concentrated Top-Rail Load (**$P_{	ext{conc}}$**)** (Required for ALL occupancies):
   

   $$
   P_{	ext{conc}} = 200	ext{ lbs}
   $$

   
   applied in any direction (outward horizontal, inward horizontal, or downward vertical) at any point along the top rail to maximize the load effect on the element under consideration.

2. **Uniform Top-Rail Load (**$w_{	ext{unif}}$**)**:

   * For `R-3_Residential` (one- and two-family dwellings and within individual R-2 dwelling units per Exception 1):
     

     $$
     w_{	ext{unif}} = 0	ext{ plf} \quad (	ext{Not Required})
     $$

   * For `Commercial_Standard`:
     

     $$
     w_{	ext{unif}} = 50	ext{ plf} \quad (	ext{applied horizontally OR vertically})
     $$

   * For `Assembly_Bleachers` (Exception 2):
     

     $$
     w_{	ext{unif},H} = 50	ext{ plf} \quad 	ext{AND} \quad w_{	ext{unif},V} = 50	ext{ plf} \quad (	ext{simultaneous})
     $$

     
     *(Note:* $P_{	ext{conc}}$ *and* $w_{	ext{unif}}$ *are NOT required to act concurrently).*

3. **Infill Component Normal Load (**$P_{	ext{infill}}$**)**:
   

   $$
   P_{	ext{infill}} = 50	ext{ lbs} \quad 	ext{over } 1.0	ext{ ft} 	imes 1.0	ext{ ft area}
   $$

4. **Structural Glass Safety Factor (`IBC Section 2407.1`)**:

   * If $ext{Infill} == 	ext{Structural\_Glass}$, apply safety factor $ext{FS}_{	ext{glass}} = 4.0$ to glass panel and glass shoe/clamp stress checks.

### Step 2: Top Rail Bending & Shear Demands (Span $S_{	ext{post}}$)

1. **Case 1: Concentrated Load** $P_{	ext{conc}} = 200	ext{ lbs}$ **at Midspan of Top Rail**:
   

   $$
   M_{	ext{rail,conc}} = rac{P_{	ext{conc}} \cdot S_{	ext{post}}}{4} \quad (	ext{lb-ft}), \qquad V_{	ext{rail,conc}} = rac{P_{	ext{conc}}}{2} = 100	ext{ lbs}
   $$

2. **Case 2: Uniform Load** $w_{	ext{unif}} = 50	ext{ plf}$ **Along Top Rail** (if applicable):
   

   $$
   M_{	ext{rail,unif}} = rac{w_{	ext{unif}} \cdot S_{	ext{post}}^2}{8} \quad (	ext{lb-ft}), \qquad V_{	ext{rail,unif}} = rac{w_{	ext{unif}} \cdot S_{	ext{post}}}{2} \quad (	ext{lbs})
   $$

3. **Governing Unfactored Top Rail Live Demand**:
   

   $$
   M_{	ext{rail},L} = \max(M_{	ext{rail,conc}}, M_{	ext{rail,unif}}), \qquad V_{	ext{rail},L} = \max(V_{	ext{rail,conc}}, V_{	ext{rail,unif}})
   $$

### Step 3: Guardrail Post & Base Connection Demands

1. **Effective Moment Arm to Post Base Connection (**$H_{	ext{eff}}$**)**:
   

   $$
   H_{	ext{eff}} = rac{H_{	ext{guard}} + e_{	ext{fas}}}{12} \quad (	ext{ft})
   $$

2. **Horizontal Shear at Top of Single Post (**$V_{	ext{post},L}$**)**:

   * Under concentrated load $P_{	ext{conc}} = 200	ext{ lbs}$ applied directly at the top of the post:
     

     $$
     V_{	ext{post,conc}} = 200	ext{ lbs}
     $$

   * Under uniform load $w_{	ext{unif}} = 50	ext{ plf}$ over tributary post spacing $S_{	ext{post}}$:
     

     $$
     V_{	ext{post,unif}} = w_{	ext{unif}} \cdot S_{	ext{post}} \quad (	ext{lbs})
     $$

   * Governing Live Load Post Shear:
     

     $$
     V_{	ext{post},L} = \max(V_{	ext{post,conc}}, V_{	ext{post,unif}})
     $$

     
     *(Note: For residential guards or commercial guards with* $S_{	ext{post}} \le 4.0	ext{ ft}$*, the* $200	ext{ lb}$ *concentrated load always governs:* $50	ext{ plf} 	imes 4.0	ext{ ft} = 200	ext{ lbs}$*; for commercial guards with* $S_{	ext{post}} > 4.0	ext{ ft}$*, the* $50	ext{ plf}$ *uniform load governs post design).*

3. **Exterior Wind Shear on Post (**$V_{	ext{post},W}$**)**:
   

   $$
   V_{	ext{post},W} = p_W \cdot \epsilon_{	ext{guard}} \cdot S_{	ext{post}} \cdot \left(rac{H_{	ext{guard}}}{12} ight) \quad (	ext{lbs})
   $$

   
   where Wind load acts at mid-height of the guard ($H_{	ext{wind,arm}} = rac{0.5 H_{	ext{guard}} + e_{	ext{fas}}}{12}	ext{ ft}$).

4. **Overturning Moment at Post Base / Rim Joist (**$M_{	ext{base}}$**)**:

   * Live Load Overturning Moment:
     

     $$
     M_{	ext{base},L} = V_{	ext{post},L} \cdot H_{	ext{eff}} \quad (	ext{lb-ft})
     $$

   * Wind Load Overturning Moment:
     

     $$
     M_{	ext{base},W} = V_{	ext{post},W} \cdot H_{	ext{wind,arm}} \quad (	ext{lb-ft})
     $$

### Step 4: Factored Design Loads (ASD vs. LRFD)

Apply load combinations from `ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv` ([ASCE 7-22 Chapter 2](https://pdfcoffee.com/asce-7-22-ch-02-for-pc-2-pdf-free.html)):

* **ASD (Allowable Stress Design)**:
  

  $$
  V_{	ext{ASD}} = \max\left(1.0 V_{	ext{post},L},\ 0.6 V_{	ext{post},W},\ 0.75 V_{	ext{post},L} + 0.45 V_{	ext{post},W} ight)
  $$

  $$
  M_{	ext{base,ASD}} = \max\left(1.0 M_{	ext{base},L},\ 0.6 M_{	ext{base},W},\ 0.75 M_{	ext{base},L} + 0.45 M_{	ext{base},W} ight)
  $$

* **LRFD (Strength Design)**:
  

  $$
  V_{	ext{LRFD}} = \max\left(1.6 V_{	ext{post},L},\ 1.0 V_{	ext{post},W},\ 1.0 V_{	ext{post},L} + 1.0 V_{	ext{post},W} ight)
  $$

  $$
  M_{	ext{base,LRFD}} = \max\left(1.6 M_{	ext{base},L},\ 1.0 M_{	ext{base},W},\ 1.0 M_{	ext{base},L} + 1.0 M_{	ext{base},W} ight)
  $$

### Step 5: Resolution of Base Overturning Moment into Fastener Forces

1. **Case A: Surface-Mounted Steel Post Base Plate on Concrete/Wood Deck** (bolt lever arm $d_{	ext{bolt}}$ from tension bolt row to compression edge of base plate, in inches):

   * Total Tension Force in Anchor Bolt / Lag Screw Row ($N_t$ bolts in tension row):
     

     $$
     T_{	ext{bolt}} = rac{M_{	ext{base}} \cdot 12}{N_t \cdot d_{	ext{bolt}}} \quad (	ext{lbs/bolt})
     $$

   * Base Plate Bending Moment (at weld/face of HSS post, cantilever distance $c_{	ext{plate}}$ from bolt centerline to post face):
     

     $$
     M_{	ext{plate}} = N_t \cdot T_{	ext{bolt}} \cdot c_{	ext{plate}} \quad (	ext{lb-in.})
     $$

2. **Case B: Fascia-Mounted Wood/Steel Post on Rim Joist / Blocking** (upper tension connector and lower bearing/bolt separated vertically by $d_v$ in inches):

   * Upper Holdown / Through-Bolt Tension Force (coupled into deck framing via tension tie such as Simpson DTT2Z/HDU2 into joist, NEVER relying on cross-grain bending of rim joist):
     

     $$
     T_{	ext{upper}} = rac{M_{	ext{base}} \cdot 12}{d_v} \quad (	ext{lbs})
     $$

## 4. Output DTO (`GuardrailLoadsOutputDTO`) & Downstream Routing

* `V_rail_ASD`, `M_rail_ASD`, `V_rail_LRFD`, `M_rail_LRFD`: Top rail shear and bending demands

* `V_post_ASD`, `M_base_ASD`, `V_post_LRFD`, `M_base_LRFD`: Post base shear and overturning moment demands

* `T_bolt_ASD`, `T_bolt_LRFD`: Tension force per anchor bolt / holdown tie at post base

* **Downstream Connection Modules**:

  * Wood post-to-rim-joist bolt & tension tie $ightarrow$ `nds/wood_bolt_dowel_calc.py` & `nds/wood_lag_screw_calc.py`

  * Steel HSS post weld & base plate bending $ightarrow$ `aisc360/steel_weld_bolt_calc.py`

  * Concrete slab edge anchor bolt breakout/pullout $ightarrow$ `aci318/concrete_anchor_bolt_calc.py`

## 5. Reference Verification Example

* **Input**: Residential exterior deck guardrail (`R-3_Residential` under 2025 CBC with $H_{	ext{guard}} = 42	ext{ in.}$), post spacing $S_{	ext{post}} = 5.0	ext{ ft}$, surface-mounted $2.5"	imes 2.5"$ HSS steel post on a $6"	imes 6"$ base plate with $N_t = 2$ tension anchors at lever arm $d_{	ext{bolt}} = 4.25	ext{ in.}$ ($e_{	ext{fas}} = 0	ext{ in.}$).

* **Calculation**:

  1. Live load per `IBC Section 1607.9.1.1`: $P_{	ext{conc}} = 200	ext{ lbs}$ at top of post ($H_{	ext{eff}} = 42 / 12 = 3.50	ext{ ft}$).

  2. **ASD Post Base Demand**:

     * $V_{	ext{post,ASD}} = 200	ext{ lbs}$

     * $M_{	ext{base,ASD}} = 200	ext{ lbs} 	imes 3.50	ext{ ft} = 700	ext{ lb-ft} = 8,400	ext{ lb-in.}$

  3. **ASD Anchor Bolt Tension**:

     * $T_{	ext{bolt,ASD}} = rac{8,400	ext{ lb-in.}}{2 	imes 4.25	ext{ in.}} = 988.2	ext{ lbs/bolt}$

  4. **LRFD Anchor Bolt Tension** ($1.6L$):

     * $T_{	ext{bolt,LRFD}} = 1.6 	imes 988.2 = 1,581.2	ext{ lbs/bolt}$.