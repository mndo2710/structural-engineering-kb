# Wood Shear Wall Design Procedure (NDS / SDPWS / IBC / CBC)

### 1. References
- 2024 IBC / 2022-2025 CBC Chapter 23
- ANSI/AWC SDPWS Table 4.3A
- ASCE 7-22 Chapter 12

### 2. Design Steps
1. Compute unit shear demand: $v = V / L$ (plf).
2. Check aspect ratio $h/b \le 3.5:1$ (for blocked WSP) or $2:1$ (unblocked).
3. Lookup sheathing and nailing schedule from `database/nds_wood/v2024/sdpws/table_4_3a_shear_walls.csv`.
4. Calculate overturning moment: $M_{ot} = V \times h$.
5. Calculate resisting dead load moment: $M_r = 0.6 D \times b/2$.
6. Net tension uplift: $T = (M_{ot} - M_r) / d$.
7. Select Simpson Holdown from `database/manufacturer_catalogs/simpson_strong_tie/holdowns_hdu_sthd_dtt.csv`.
8. Check foundation anchorage (shear sliding and anchor bolt pullout).
