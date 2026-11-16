# Wood Joist Hanger & Roof-to-Wall Hurricane Tie Design Procedure (NDS 2024 / Simpson C-C-2026)

## 1. General & Code Basis
- **Governing Codes & Standards**:
  - **2024 International Building Code (IBC)** / **2025 California Building Code (CBC)**, Chapter 23 ([IBC Chapter 23](https://bayarearetrofit.com/wp-content/uploads/2015-Wind-and-Seismic.pdf)).
  - **ANSI/AWC NDS-2024**: *National Design Specification for Wood Construction*, Chapter 11 & 12 (Mechanical Connections & Wood Member Bearing/Shear Checks).
  - **ASCE/SEI 7-22**: *Minimum Design Loads and Associated Criteria for Buildings and Other Structures*, Chapter 30 (Components & Cladding Wind Uplift on Roof Rafters/Trusses) & Chapter 2 (Load Combinations).
  - **Simpson Strong-Tie Wood Construction Connectors Catalog (C-C-2026)**:
    - Face-Mount & Concealed-Flange Joist Hangers: [LUS Series](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/lus_hanger/p/lus), [HU/HUC Series](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hu_hanger/p/hu), [HUS Series](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hus_hanger/p/hus), [HHUS Series](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hhus_hanger/p/hhus), [HGUS Series](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hgus_hanger/p/hgus), [HUCQ Series](https://www.strongtie.com/concealedflangehangers_engineeredwoodconnectors/hucq_hanger/p/hucq), [IUS Series](https://www.strongtie.com/facemounthangersewp_engineeredwoodconnector/ius_hanger/p/ius), [MIU Series](https://www.strongtie.com/facemounthangersewp_engineeredwoodconnector/miu_hanger/p/miu).
    - Seismic & Hurricane Ties: [H1A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h1a_htie/p/h1a), [H2.5A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h25a_htie/p/h25a), [H2.5T](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h25t_htie/p/h25t), [H3](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h3_htie/p/h3), [H8](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h8_htie/p/h8), [H10A / H10A-2 / H10S](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h10a_htie/p/h10a).
- **Referenced Repository Databases**:
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv`
  - `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`
- **Design Philosophies**:
  - Simpson Strong-Tie catalog tables publish **Allowable Stress Design (ASD)** loads calibrated to standard NDS load duration factors:
    - **Floor Download**: $C_D = 1.00$ ($D + L$).
    - **Snow Download**: $C_D = 1.15$ ($D + S$).
    - **Roof Download**: $C_D = 1.25$ ($D + L_r$).
    - **Wind / Seismic Uplift & Lateral ($F_1, F_2$)**: $C_D = 1.60$ ($0.6D + 0.6W$ or $0.6D + 0.7E$).
  - For **LRFD** checks, convert Simpson ASD capacities using the ASTM D5457 / ICC-ES format conversion factor ($K_F / \phi$), or compare ASD load combinations directly against catalog values.

---

## 2. Required Input Parameters

| Parameter Symbol | Description | Units | Typical / Source Reference |
| :--- | :--- | :--- | :--- |
| $b_{joist} \times d_{joist}$ | Actual width and depth of carried joist, rafter, truss, or beam | $\text{in.}$ | Framing Plan (`2x6` to `4x16`, `1-3/4" x 11-7/8"` LVL/TJI) |
| $t_{header}$ | Actual thickness of carrying header, ledger, or top plates | $\text{in.}$ | Framing Plan (`1.5"` single ply vs. `3.0"` double ply vs. `3.5"` 4x) |
| $\text{Species}_{header}, \text{Species}_{joist}$ | Wood species group (`DF/SP` $G \ge 0.50$ vs. `SPF/HF` $G = 0.42$–$0.43$) | — | General Notes / NDS Table 12.3.3A |
| $R_{floor}, R_{snow}, R_{roof}$ | ASD gravity download reaction at joist/beam end | $\text{lbs}$ | Joist/Beam Reaction Takedown |
| $U_{ASD}$ | Net ASD Wind or Seismic uplift reaction at support ($0.6W - 0.6D$) | $\text{lbs}$ | Roof C&C Wind Uplift / Truss Reaction |
| $F_{1,ASD}$ | ASD lateral force parallel to wall top plate (in-plane shear transfer) | $\text{lbs}$ | Diaphragm-to-Wall Unit Shear $\times s_{rafter}$ |
| $F_{2,ASD}$ | ASD lateral force perpendicular to wall top plate (out-of-plane wind/seismic) | $\text{lbs}$ | Wall Out-of-Plane Anchorage Reaction |
| $\theta_{slope}, \theta_{skew}$ | Joist slope angle (up/down from horizontal) and horizontal skew angle | $\text{deg}$ | Roof Pitch / Framing Geometry |

---

## 3. Adjustment Factors & Governing Mechanics

### 3.1 Double-Shear Nailing Mechanics (`LUS`, `HUS`, `HHUS`, `HGUS`)
- Hangers featuring patented **double-shear dome nailing** ([LUS](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/lus_hanger/p/lus), [HUS](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hus_hanger/p/hus), [HHUS](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hhus_hanger/p/hhus), [HGUS](https://www.strongtie.com/facemounthangersssl_solidsawnlumberconnector/hgus_hanger/p/hgus)) drive the joist nails at a $45^\circ$ angle through the carried joist side and into the carrying header, creating **two shear planes per joist nail** (one at the hanger-to-joist interface, and one at the joist-to-header wood-to-wood interface).
- **Mandatory Full-Length Joist Nail Rule**:
  - Tabulated double-shear downloads require $3\text{ in.}$ (`0.148" x 3"` 10d common) or $3\text{-}1/2\text{ in.}$ (`0.162" x 3.5"` 16d common) joist nails.
  - **Reduction if Short Joist Nails Are Used**: If $1\text{-}1/2\text{ in.}$ (`0.148" x 1.5"`) joist nails are mistakenly installed in the double-shear dome holes of an `LUS` hanger, the joist nails do not penetrate the header (single shear only), reducing the allowable download capacity to **$0.64 \times P_{allow,tabulated}$**.

### 3.2 Carrying Member (Header) Thickness & Species Governing Rule
- **Governing Species**: If the carried joist and carrying header have different specific gravities (e.g., `DF-L` LVL carried by an `SPF` rim board or header), use the **lower species table (`SPF/HF`)** for both header and joist fasteners.
- **Minimum Header Thickness for Full-Length Nails/Screws**:
  - Standard `0.148" x 3"` (10d), `0.162" x 3.5"` (16d), and `1/4" x 2.5"` `SDS2.5` header fasteners require a **minimum $3.0\text{ in.}$ (2-ply 2x) carrying header** so fasteners do not protrude out the back face or lose withdrawal/bearing length.
  - For a single `2x` ($1.5"$ thick) ledger or header, specify `0.148" x 1.5"` nails or `#9 x 1.5"` `SD9112` screws (`LUS (SD Screws)` rows in `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv`).

### 3.3 Hurricane Tie Multi-Axis Simultaneous Loading Rules (Unity Equation vs. 75% Rule)
When a roof-to-wall connector ([H1A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h1a_htie/p/h1a), [H2.5A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h25a_htie/p/h25a), [H10A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h10a_htie/p/h10a)) resists simultaneous **Wind Uplift ($U$)** and **Lateral Loads ($F_1$ parallel to plate, $F_2$ perpendicular to plate)** under the same ASCE 7 load combination (e.g., $0.6D + 0.6W$):
1. **Standard Linear Interaction (Unity Equation - Conservative & Universally Accepted)**:
   $$\frac{U_{ASD}}{U_{allow}} + \frac{F_{1,ASD}}{F_{1,allow}} + \frac{F_{2,ASD}}{F_{2,allow}} \le 1.00$$
2. **Simpson Strong-Tie 75% Rule (Catalog General Notes for Multi-Directional Connectors)**:
   - Where explicitly permitted by the connector series footnotes (such as `H1A` and `H10A` tested in three orthogonal directions), simultaneous loading in more than one direction is permitted provided the design load in each individual direction does not exceed **$75\%$ ($0.75\times$) of the published allowable load** in that direction:
     $$U_{ASD} \le 0.75 \cdot U_{allow}, \qquad F_{1,ASD} \le 0.75 \cdot F_{1,allow}, \qquad F_{2,ASD} \le 0.75 \cdot F_{2,allow}$$
   - **Plan Check Best Practice**: Always report **both** the Linear Unity Ratio and the $75\%$ Rule check in calculation sheets so building department reviewers see full compliance under either interpretation.

---

## 4. Step-by-Step Calculation Procedure

### Part A: Gravity & Uplift Joist / Beam Hanger Design
1. **Step A1 — Reaction Determination**:
   - Determine carried member end reactions for all applicable load durations:
     - $R_{floor}$ ($D + L$, $C_D = 1.00$)
     - $R_{snow}$ ($D + S$, $C_D = 1.15$)
     - $R_{roof}$ ($D + L_r$, $C_D = 1.25$)
     - $U_{ASD}$ ($0.6D + 0.6W$ or $0.6D + 0.7E$, $C_D = 1.60$)
2. **Step A2 — Geometry & Hanger Series Selection**:
   - Verify carried member width $W_{joist}$ and depth $H_{joist}$. Ensure hanger stirrup height $H \ge 0.60 \cdot H_{joist}$ to prevent top-edge rotation of the carried member (unless lateral blocking is provided at top edge).
   - Select hanger model from `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv` (`LUS` for light-to-medium joists, `HUS`/`HHUS`/`HGUS` for heavy girders/trusses, `HUC`/`HUCQ` where concealed flanges are required at end conditions, `IUS`/`MIU` for wood I-joists and SCL).
3. **Step A3 — Download & Uplift Capacity Verification**:
   - Look up `DF/SP` or `SPF/HF` allowable loads based on the **lesser** specific gravity of the carried and carrying members:
     $$D/C_{down} = \max\left(\frac{R_{floor}}{P_{allow,100}},\; \frac{R_{snow}}{P_{allow,115}},\; \frac{R_{roof}}{P_{allow,125}}\right) \le 1.00$$
     $$D/C_{uplift} = \frac{U_{ASD}}{U_{allow,160}} \le 1.00$$
4. **Step A4 — Carrying Header Side-Loaded Cross-Grain & Shear Check (NDS Section 3.4.3.3)**:
   - Where a heavy concentrated hanger load ($P > 3,000\text{ lbs}$, e.g. `HHUS` or `HGUS`) is attached to the lower half of a carrying wood girder rather than bearing on top, verify the effective shear capacity of the carrying girder at the connection per NDS Equation 3.4-6 ($V'_r$ reduction for connections with $d_e < d$), and ensure hanger fasteners extend into the upper half of the carrying beam.

### Part B: Roof-to-Wall Hurricane Tie Design
1. **Step B1 — Resolve Roof-to-Wall Forces per Rafter/Truss Spacing ($s_{rafter}$)**:
   - **Net Wind Uplift per Rafter ($U_{ASD}$)**:
     $$U_{ASD} = \left(p_{net,0.6W} - 0.6 \cdot w_{DL,roof}\right) \cdot A_{trib,rafter} \quad (\text{lbs})$$
   - **In-Plane Diaphragm Shear per Rafter ($F_{1,ASD}$)**:
     $$F_{1,ASD} = v_{dia,ASD} \cdot \left(\frac{s_{rafter}}{12}\right) \quad (\text{lbs})$$
   - **Out-of-Plane Wall Reaction per Rafter ($F_{2,ASD}$)**:
     $$F_{2,ASD} = w_{wall,ASD} \cdot \left(\frac{h_{wall}}{2}\right) \cdot \left(\frac{s_{rafter}}{12}\right) \quad (\text{lbs})$$
2. **Step B2 — Select Hurricane Tie Model (`Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`)**:
   - Look up `Uplift`, `F1`, and `F2` allowable capacities ($C_D = 1.60$) for the governing wood species (`DF/SP` vs. `SPF/HF`).
3. **Step B3 — Check Individual Directions & Simultaneous Multi-Axis Interaction**:
   - Individual Direction Checks:
     $$\frac{U_{ASD}}{U_{allow}} \le 1.00, \qquad \frac{F_{1,ASD}}{F_{1,allow}} \le 1.00, \qquad \frac{F_{2,ASD}}{F_{2,allow}} \le 1.00$$
   - Simultaneous Wind Combination ($U + F_2$ or $U + F_1 + F_2$):
     - **Linear Unity Check**:
       $$D/C_{unity} = \frac{U_{ASD}}{U_{allow}} + \frac{F_{1,ASD}}{F_{1,allow}} + \frac{F_{2,ASD}}{F_{2,allow}} \le 1.00$$
     - **Simpson 75% Rule Check**:
       $$\max\left(\frac{U_{ASD}}{0.75 \cdot U_{allow}},\; \frac{F_{1,ASD}}{0.75 \cdot F_{1,allow}},\; \frac{F_{2,ASD}}{0.75 \cdot F_{2,allow}}\right) \le 1.00$$

---

## 5. Limit States Summary & Demand-to-Capacity Ratios ($D/C$)

| Limit State / Component | Demand Symbol | Capacity Symbol | Governing Code / Catalog Reference | Acceptance Criterion |
| :--- | :--- | :--- | :--- | :--- |
| **Hanger Stirrup Height Ratio** | $0.60 \cdot H_{joist}$ | $H_{hanger}$ ($\text{in.}$) | Simpson C-C-2026 General Hanger Notes | $0.60 H_{joist} / H_{hanger} \le 1.00$ |
| **Hanger Floor Download ($1.00$)** | $R_{floor}$ ($\text{lbs}$) | $P_{allow,100}$ ($\text{lbs}$) | `Simpson_C-C-2026_Joist_Hangers_...csv` | $R_{floor} / P_{allow,100} \le 1.00$ |
| **Hanger Roof/Snow Download** | $R_{roof}$ or $R_{snow}$ | $P_{allow,125}$ or $P_{allow,115}$ | `Simpson_C-C-2026_Joist_Hangers_...csv` | $R_{demand} / P_{allow} \le 1.00$ |
| **Hanger Wind/Seismic Uplift** | $U_{ASD}$ ($\text{lbs}$) | $U_{allow,160}$ ($\text{lbs}$) | `Simpson_C-C-2026_Joist_Hangers_...csv` | $U_{ASD} / U_{allow,160} \le 1.00$ |
| **Hurricane Tie Uplift ($C_D=1.6$)** | $U_{ASD}$ ($\text{lbs}$) | $U_{allow}$ ($\text{lbs}$) | `Simpson_C-C-2026_Hurricane_Ties_...csv` | $U_{ASD} / U_{allow} \le 1.00$ |
| **Hurricane Tie Lateral ($F_1, F_2$)** | $F_{1,ASD}, F_{2,ASD}$ | $F_{1,allow}, F_{2,allow}$ | `Simpson_C-C-2026_Hurricane_Ties_...csv` | $F_i / F_{i,allow} \le 1.00$ |
| **Multi-Axis Interaction** | $\sum (F_i / F_{i,allow})$ | $1.00$ (Unity) / $0.75$ Rule | Simpson C-C-2026 Hurricane Tie Notes | $D/C_{unity} \le 1.00$ |

---

## 6. Detailing Requirements & Plan Check Red Flags (QA/QC)
1. **Single-Sided Twist Ties (`H2.5A`, `H3`, `H8`) Lateral Directionality ([Simpson H2.5A Page](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h25a_htie/p/h25a))**:
   - Single-sided ties (`H2.5A`, `H3`, `H8`) have very low lateral $F_1$ capacity ($85\text{ to }130\text{ lbs}$ with nails) and require load $F_1$ to push **into** the tie flange unless installed in **symmetric pairs** on opposite sides of the rafter/truss. Where hurricane ties are used to transfer roof diaphragm shear ($F_1$) into the top plate without solid blocking, specify U-shaped ties (`H1A` or `H10A`) or paired `H2.5A` ties.
2. **Continuous Load Path Through Double Top Plates (`H10S` vs. Upper-Plate-Only Attachment)**:
   - Most hurricane ties (`H1A`, `H2.5A`, `H10A`) nail into the **upper top plate** (or straddle both top plates depending on placement). Ensure the upper top plate is adequately face-nailed to the lower top plate, and the lower top plate is anchored to the studs below (`H10S` provides a direct continuous path into the stud with `(8) 8d x 2.5"` stud nails) ([Simpson H10A/H10S Page](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h10a_htie/p/h10a)).
3. **Web Stiffeners Required for Wood I-Joists in Double-Shear Hangers**:
   - If an `LUS` or `HUS` face-mount hanger with double-shear nailing is used on a wood I-joist instead of an `IUS` or `MIU` hanger, **full-height wood web stiffeners** must be installed on both sides of the I-joist web so the angled double-shear nails have solid wood backing.
4. **Multi-Ply Truss / Girder Fastening**:
   - When a 2-ply or 3-ply girder (`LUS210-2`, `HHUS410`, `HGUS5.50/12`) is supported by a hanger, the plies must be nailed, screwed (`SDWS`), or bolted together along their length so the plies act as a single composite unit and do not separate behind the front ply.

---

## 7. Fully Worked Numerical Design Example (US Customary Units)

### 7.1 Problem Statement
1. **Part A (Joist Hanger)**: Design a face-mount hanger supporting a **2-ply `2x10` DF-L roof girder** ($3.0" \times 9.25"$) framing into a **3-ply `2x12` DF-L carrying header** ($4.5" \times 11.25"$):
   - Gravity Roof Download ($D + L_r$, $C_D = 1.25$): $R_{roof} = 3,150\text{ lbs}$.
   - Gravity Floor/Dead Load ($D + L$, $C_D = 1.00$): $R_{floor} = 2,600\text{ lbs}$.
   - Net Wind Uplift ($0.6D + 0.6W$, $C_D = 1.60$): $U_{girder} = 1,450\text{ lbs}$.
2. **Part B (Roof-to-Wall Hurricane Tie)**: Design a hurricane tie for **`2x8` SPF rafters at $24"\text{ o.c.}$** bearing on a **`2x6` SPF double top plate** subjected to simultaneous Wind Uplift and Lateral Wind loads ($0.6D + 0.6W$, $C_D = 1.60$):
   - Net Wind Uplift per rafter: $U_{ASD} = 520\text{ lbs}$.
   - In-plane diaphragm unit shear $v_{ASD} = 160\text{ plf} \implies F_{1,ASD} = 160 \times (24 / 12) = 320\text{ lbs/rafter}$.
   - Out-of-plane wall top reaction: $F_{2,ASD} = 95\text{ lbs/rafter}$.

### 7.2 Step-by-Step Solution

#### Part A: 2-Ply `2x10` Girder Hanger (`Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv`)
1. **Check `LUS210-2` first**:
   - From `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv`, `LUS210-2` (`18 ga`, `(8) 0.162"x3.5"` header nails + `(6) 0.162"x3.5"` double-shear joist nails) in `DF/SP` has:
     - $P_{allow,100} = 2,215\text{ lbs} < 2,600\text{ lbs}$ (NG for Floor Download).
     - $P_{allow,125} = 2,750\text{ lbs} < 3,150\text{ lbs}$ (NG for Roof Download).
2. **Upgrade to `HUS210-2`** (`14 ga`, $W = 3.125", H = 9.0", B = 3.0"$):
   - Header thickness check: $t_{header} = 4.5" \ge 3.0"$ required for `0.162" x 3.5"` (16d common) nails $\implies \textbf{OK}$.
   - Stirrup height check: $H = 9.0" \ge 0.60 \times 9.25" = 5.55" \implies \textbf{OK}$.
   - From `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv` for `HUS210-2` with `(30) 0.162"x3.5"` header nails and `(10) 0.162"x3.5"` double-shear joist nails in `DF/SP`:
     - **Floor Download ($C_D = 1.00$)**:
       $$P_{allow,100} = 5,115\text{ lbs} \ge 2,600\text{ lbs} \quad (D/C = 0.508 \le 1.00) \implies \textbf{OK}$$
     - **Roof Download ($C_D = 1.25$)**:
       $$P_{allow,125} = 5,615\text{ lbs} \ge 3,150\text{ lbs} \quad (D/C = 0.561 \le 1.00) \implies \textbf{OK}$$
     - **Wind Uplift ($C_D = 1.60$)**:
       $$U_{allow,160} = 3,165\text{ lbs} \ge 1,450\text{ lbs} \quad (D/C = 0.458 \le 1.00) \implies \textbf{OK}$$
   - **Use Simpson `HUS210-2`**.

#### Part B: `2x8` SPF Rafter Hurricane Tie (`Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv`)
1. **Check `H2.5A` (Nails)**:
   - In `SPF/HF`, `H2.5A` has $U_{allow} = 485\text{ lbs} < 520\text{ lbs}$ and $F_{1,allow} = 110\text{ lbs} < 320\text{ lbs}$ $\implies \text{NG}$.
2. **Try Simpson [H10A](https://www.strongtie.com/seismicandhurricaneties_strapsandties/h10a_htie/p/h10a)** (`18 ga` U-shaped hurricane tie with `(9) 0.148" x 1.5"` nails to rafter and `(9) 0.148" x 1.5"` nails to top plates):
   - From `Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv` for **`SPF/HF`** ($C_D = 1.60$):
     - $U_{allow} = 1,015\text{ lbs}$
     - $F_{1,allow} = 485\text{ lbs}$
     - $F_{2,allow} = 285\text{ lbs}$
3. **Individual Direction & 75% Rule Checks**:
   - **Uplift**: $U_{ASD} / U_{allow} = 520 / 1,015 = 0.512 \le 0.75 \implies \textbf{OK}$.
   - **Lateral $F_1$ (In-Plane)**: $F_{1,ASD} / F_{1,allow} = 320 / 485 = 0.660 \le 0.75 \implies \textbf{OK}$.
   - **Lateral $F_2$ (Out-of-Plane)**: $F_{2,ASD} / F_{2,allow} = 95 / 285 = 0.333 \le 0.75 \implies \textbf{OK}$.
4. **Simultaneous Multi-Axis Interaction Check**:
   - Note that peak in-plane diaphragm shear ($F_1$, wind parallel to ridge) and peak out-of-plane wall wind ($F_2$, wind normal to ridge) occur under orthogonal wind directions, whereas Uplift ($U$) acts simultaneously with either $F_1$ or $F_2$:
     - **Case 1 ($U + F_1$) Linear Unity Ratio**:
       $$D/C_{U+F1} = \frac{520}{1,015} + \frac{320}{485} = 0.512 + 0.660 = 1.172 > 1.00 \quad (\text{Passes 75\% Rule since } 0.512 \le 0.75 \text{ and } 0.660 \le 0.75)$$
     - **Case 2 ($U + F_2$) Linear Unity Ratio**:
       $$D/C_{U+F2} = \frac{520}{1,015} + \frac{95}{285} = 0.512 + 0.333 = 0.845 \le 1.00 \implies \textbf{OK}$$
   - If strict linear unity $\le 1.00$ is required for $U + F_1$ without relying on the $75\%$ Rule, add solid $2\text{x}$ blocking between rafters with `LTP4` clips to take $F_1$ directly, leaving `H10A` with $D/C_{U+F2} = 0.845 \le 1.00$.
