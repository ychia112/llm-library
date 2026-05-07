Run the test suite for the Python backend.

Steps:
1. Run: `pytest tests/ -v --tb=short`
2. Report: number passed, failed, errors
3. For each failure: show the test name, the assertion that failed, and the likely cause
4. If all pass: confirm and suggest any missing test coverage for recently changed files

Do not fix failures automatically — report them first and wait for confirmation.
