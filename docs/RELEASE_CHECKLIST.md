# Production Release Checklist

Use this checklist before creating a version tag. Hosted CI validates imports, tests, and frozen builds, but it cannot validate a physical webcam or site-specific recognition thresholds.

## 1. Clean install

- Install from a fresh checkout with Python 3.10 or 3.12.
- Run `python main.py --self-test` and confirm every supported module reports `ok`.
- Run `python scripts/download_face_models.py` once while online, or configure verified local model paths.
- Run `python main.py --version` and confirm it matches the intended tag.

## 2. Authentication

- Start with an empty application-data directory.
- Confirm first-run setup requires creation of an administrator password and provides no default password.
- Restart the app and confirm invalid credentials are rejected.
- Confirm `config/users.json` is written only under the user data directory and contains `scrypt-v1`, a salt, and a password hash rather than plaintext credentials.

## 3. Real camera validation

Run on every camera model intended for deployment:

```bash
python scripts/benchmark_pipeline.py --camera 0 --frames 120 --warmup 10
```

Record average/p95 latency, approximate FPS, reconnect count, and read failures. Test an intentional disconnect/reconnect while the application is open.

## 4. Recognition and liveness calibration

Use consented local test subjects and the actual deployment lighting/cameras.

- Enroll multiple clear images per subject.
- Verify enrolled live subjects are recognized consistently.
- Verify unknown live subjects remain unknown.
- Test common presentation attacks with a printed face and a face displayed on another screen.
- Tune SFace and liveness thresholds only from measured validation results; do not weaken liveness simply to improve convenience.
- Confirm automatic attendance never occurs before the temporal liveness gate passes.

## 5. Attendance and backup

- Mark attendance automatically and manually.
- Confirm duplicate same-day subject attendance updates rather than creating duplicate rows.
- Export attendance and verify the CSV matches SQLite.
- Create a backup from Settings.
- Open the backed-up SQLite file and run `PRAGMA integrity_check`; the result must be `ok`.
- Verify the backup contains current config and face-gallery/model state.

## 6. Native package validation

After CI completes, test the produced one-folder bundle on at least one real machine for each platform you intend to publish:

- Windows x64
- Linux x64
- macOS ARM64
- macOS Intel x64

Confirm startup, first-run/login, camera permission, enrollment, liveness-gated recognition, attendance persistence, settings, and local backup.

## 7. Create the release

The tag must exactly match the package version, for example:

```bash
git tag v1.5.0
git push origin v1.5.0
```

The release workflow rejects a tag/package version mismatch, builds all four native archives, smoke-tests the frozen executable, creates GitHub artifact attestations, and publishes the archives to the GitHub Release.

Verify an attested downloaded archive with GitHub CLI:

```bash
gh attestation verify <downloaded-archive> -R AaryaMody1301/Face_Detection_Attendance_System
```

## 8. Known distribution limitation

The project does not currently provide paid code-signing certificates, Windows Authenticode signing, Apple Developer ID signing/notarization, MSI installers, or DMG installers. These are distribution enhancements, not requirements for running the local application from source or the unsigned native bundles.
