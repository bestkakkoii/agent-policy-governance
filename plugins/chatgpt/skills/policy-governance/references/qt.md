# qt
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.qt
Strength: conditional; scope: ["cpp"]
Only when Qt is actually selected: prefer current Qt APIs, then current standard library, then necessary platform SDK; Qt5Compat needs justification.
Prefer value() then at() then operator[] without masking missing data/bounds. Correct parent/child ownership and actionable diagnostics are mandatory.
