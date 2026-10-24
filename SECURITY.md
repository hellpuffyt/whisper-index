# Security policy

## Supported versions

Only the latest commit on `main` receives fixes. There are no maintained release branches.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's advisory form:
https://github.com/hellpuffyt/whisper-index/security/advisories/new

Do not open a public issue for a suspected vulnerability. Include the version or commit,
a minimal reproduction, and the impact you observed. You should receive an acknowledgement
within a few days; fixes are released as soon as they are verified.

## Scope

whisper-index reads local transcript files (JSON/SRT/VTT) and JSON index files and prints results; it runs no speech model and makes no network calls. Relevant reports include: a crafted transcript or index file that executes code, writes outside `--out`, or exhausts resources disproportionately.
