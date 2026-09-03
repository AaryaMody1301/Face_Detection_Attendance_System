# Production Release Checklist

Use this checklist before creating a version tag. Hosted CI validates imports, reporting behavior, authorization policy, tests, dependency changes, and frozen builds, but it cannot validate a physical webcam or site-specific recognition thresholds.

## 1. Clean install

- Install from a fresh checkout with Python 3.11 or 3.12 using `constraints-release.txt`.
- Run `python main.py --self-test` and confirm every supported module reports `ok`.
- Run `python scripts/download_face_models.py` once while online, or configure verified local model paths.
- Run `python main.py --version` and confirm it matches the intended tag.

## 2. Authentication and authorization

- Start with an empty application-data directory.
- Confirm first-run setup requires creation of an administrator password and provides no default password.
- Restart the app and confirm invalid credentials are rejected.
- Confirm `config/users.json` is written only under the user data directory and contains `scrypt-v1`, a salt, and a password hash rather than plaintext credentials.
- Confirm an administrator can open Dashboard, Mark Attendance, Analytics, Registration, Training, and Settings.
- Confirm a teacher can view Dashboard/Analytics, mark attendance, register students, and train recognition data, but cannot open Settings.
- Confirm a standard user can view Dashboard/Analytics but cannot open Mark Attendance, Registration, Training, or Settings.
- Confirm blocked screens remain inaccessible even when their navigation method is invoked directly.

## 3. Dashboard and analytics

- Confirm the Dashboard contains no sample/demo identities or activity entries.
- Confirm dashboard totals, today's attendance, enrolled-student count, subject count, trend chart, subject chart, and recent activity match SQLite data.
- Change the Dashboard period between week/month/semester and confirm the trend refreshes.
- Confirm Analytics subject options come from the SQLite subjects table rather than fixed demo values.
- Test Week, Month, Semester, Year, and All Time filters against known attendance rows.
- Export the filtered Analytics dataset to CSV and confirm the exported rows and columns match the displayed filter.

## 4. Real camera validation

Run on every camera model intended for deployment:

```bash
python scripts/benchmark_pipeline.py --camera 0 --frames 120 --warmup 10
```

Record average/p95 latency, approximate FPS, reconnect count, and read failures. Test an intentional disconnect/reconnect while the application is open.

## 5. Recognition and liveness calibration

Use consented local test subjects and the actual deployment lighting/cameras.

- Enroll multiple clear images per subject.
- Verify enrolled live subjects are recognized consistently.
- Verify unknown live subjects remain unknown.
- Test common presentation attacks with a printed face and a face displayed on another screen.
- Tune SFace and liveness thresholds only from measured validation results; do not weaken liveness simply to improve convenience.
- Confirm automatic attendance never occurs before the temporal liveness gate passes.

## 6. Attendance and backup

- Mark attendance automatically and manually.
- Confirm duplicate same-day subject attendance updates rather than creating duplicate rows.
- Export attendance and verify the CSV matches SQLite.
- Create a backup from Settings.
- Open the backed-up SQLite file and run `PRAGMA integrity_check`; the result must be `ok`.
- Verify the backup contains current config and face-gallery/model state.

## 7. Native package validation

After CI completes, test the produced one-folder bundle on at least one real machine for each platform you intend to publish:

- Windows x64
- Linux x64
- macOS ARM64
- macOS Intel x64

Confirm startup, first-run/login, role restrictions, Dashboard/Analytics, camera permission, enrollment, liveness-gated recognition, attendance persistence, settings, Analytics CSV export, and local backup.

## 8. Create the release

The tag must exactly match the package version, for example:

```bash
git tag v1.5.0
git push origin v1.5.0
```

The release workflow rejects a tag/package version mismatch and a tag whose commit is not contained in `main`. It installs the reviewed release constraints, reruns repository hygiene and the complete test suite, builds all four native archives, smoke-tests each frozen executable, creates GitHub artifact attestations, and publishes only after every native build succeeds.

Verify an attested downloaded archive with GitHub CLI:

```bash
gh attestation verify <downloaded-archive> -R AaryaMody1301/Face_Detection_Attendance_System
```

## 9. Repository protection

Before publishing, protect `main` with a branch ruleset or branch protection rule that requires pull requests and successful CI/dependency-review checks. Protect release tags (`v*`) against deletion or unauthorized updates when the repository plan supports tag rulesets.

## 10. Known distribution limitation

The project does not currently provide paid code-signing certificates, Windows Authenticode signing, Apple Developer ID signing/notarization, MSI installers, or DMG installers. These are distribution enhancements, not requirements for running the local application from source or the unsigned native bundles.
