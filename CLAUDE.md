# Cleanup Branch Guidelines

## Code style                                                   
- Prefer deletion over addition. If a refactor grows a file, question the approach.
- Remove dead code, redundant comments, and unused abstractions immediately.
- Simpler is correct. A smaller diff is usually a better diff.
- Before adding a function, check if the file's primary purpose is still singular. If not, it's time for a new module.
- Prefer inline clarity over clever indirection; if a helper only has one caller, inline it.
- Every change must leave the code easier to read than before.