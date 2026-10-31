# Contract: VisibilityResult

**Version：** visibility.v1  

## Decision

`allow | deny | partial | unknown`

## Rules

1. Permission checks before retrieval.
2. Cross-bank default deny.
3. Claim body and verification status are controlled disclosure units.
4. If Evidence is not visible, do not disclose Verified markers.
5. AND justifications require full authorization of all parts.
6. Fail closed; deny does not disclose object existence.
