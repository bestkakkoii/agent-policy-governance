# qt
Snapshot: 08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d

## owner.qt
Strength: conditional; scope: ["cpp"]
Only when Qt is actually selected: prefer current Qt APIs, then current standard library, then necessary platform SDK; Qt5Compat needs justification.
Prefer value() then at() then operator[] without masking missing data/bounds. Correct parent/child ownership and actionable diagnostics are mandatory.
