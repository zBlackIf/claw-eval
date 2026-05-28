"""
Legacy builder — keep for reference but DO NOT USE.
Hand-coded atom coords below were introduced in commit a41f93c.
Running this produces input.data with atoms outside box bounds.
See the failure in step2_minimize_error.log.

The replacement lives in build_correct_hydrate.py (you write that).
"""
import sys

# Hard-coded 192 atom lines below were the bug source; elided for brevity.
# All positions were typed from a paper's Table 2 without carrying the
# unit-cell translation. First few lines:
HEADER = """LAMMPS data file for sI hydrate (LEGACY - BROKEN)

192 atoms
46 bonds
46 angles
"""

ATOMS_LEGACY = [
    "1 1 1 0.0000 0.2500 0.5000 0.2500",
    "2 1 2 0.5897 0.2500 0.5345 0.1832",
    # ... 190 more lines, many outside the 0..1 fractional box after typo
]


def main():
    print("step1_create_data.py is deprecated; use build_correct_hydrate.py",
          file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
