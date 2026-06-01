# Hydrate compression — build the LAMMPS data file from first principles

A molecular-dynamics project: compress a single I-type natural-gas hydrate
unit cell (CH₄·5.75 H₂O, sI structure) under 1 MPa / 273.5 K using
TIP4P/Ice + OPLS-UA force fields, strain rate 10⁷ s⁻¹. The previous attempt
used `step1_create_data.py` (shipped here) which **hand-coded atom
positions with rounding errors** — the resulting `input.data` crashed
`read_data` with "Atoms not in box" on step2_minimize.lmp.

## What you must produce

`build_correct_hydrate.py` — a **replacement** for step1 that:

1. Uses the canonical sI water cage geometry:
   - 46 water molecules per unit cell arranged in 2 × 5¹² + 6 × 5¹²6²
     cages
   - 8 methane molecules (1 per 5¹²6², 1 per 5¹², with cage-occupancy
     CH₄:H₂O = 8:46 for full stoichiometry)
   - Cubic box, `a = 12.03 Å` (sI lattice constant, 273 K)
2. Writes a LAMMPS `data` file with atom_style `full`:
   - `Masses` section with exactly 4 types (1=O, 2=H, 3=M-site for
     TIP4P/Ice, 4=C of CH₄ as united atom)
   - `Atoms` section — columns: atom-ID mol-ID type charge x y z
   - Charges: O = 0.0, H = +0.5897, M = −1.1794, C_UA = 0.0 (TIP4P/Ice values)
3. `Bonds` section lists O–H bonds per water (46 waters × 2 = 92 bonds)
4. `Angles` section lists H–O–H angles per water (46 angles)
5. CLI: `python3 build_correct_hydrate.py --out input.data`
6. **Post-write self-check** (required): the script re-opens the file
   and asserts: total atoms == 46×4 + 8 (= 192), box bounds ±0 … a,
   no atom has |x|,|y|,|z| > a + 0.1 Å.

## Constraints

- Stdlib + numpy only. No `ase` / `pymatgen` / other cheminformatics libs
  (production infra doesn't have them)
- Do NOT edit `step2_minimize.lmp` / `step3_nvt.lmp` / `step5_compress.lmp`
  — they read `input.data` as-is
- Do NOT hand-code explicit atom lines by hard-coded coordinates; use
  the sI-cage lattice generator pattern (nested loops over unit-cell
  basis vectors)
- If the self-check assertion fires, exit with non-zero and print the
  offending atom index
