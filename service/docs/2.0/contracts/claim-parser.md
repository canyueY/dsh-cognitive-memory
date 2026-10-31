# Contract: Claim Parser

**Version：** claim.parser.v1  

Pipeline: Raw → Rule Parser → (optional model) → AST Validator → Parse Confidence → Candidate.

Parse confidence ≠ evidence confidence. Illegal AST must not persist as normal Claim. Unexpressible → Unresolved.
