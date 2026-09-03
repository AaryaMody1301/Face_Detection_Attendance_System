# Runtime Model Licenses and Provenance

The application source code is licensed separately under this repository's `LICENSE`. Neural-network model binaries are downloaded at runtime and retain their upstream licenses and notices. They are not committed to this repository.

## YuNet face detector

- Runtime file: `face_detection_yunet_2023mar.onnx`
- Upstream: OpenCV Zoo, `models/face_detection_yunet`
- Pinned OpenCV Zoo commit: `47534e27c9851bb1128ccc0102f1145e27f23f98`
- SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- Expected size: `232589` bytes
- Upstream model-directory license: MIT
- Local override: `FACE_YUNET_MODEL`

The application verifies the exact size and SHA-256 before accepting a downloaded cached copy.

## SFace recognizer

- Runtime file: `face_recognition_sface_2021dec.onnx`
- Upstream: OpenCV Zoo, `models/face_recognition_sface`
- Pinned OpenCV Zoo commit: `47534e27c9851bb1128ccc0102f1145e27f23f98`
- SHA-256: `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`
- Expected size: `38696353` bytes
- Upstream model-directory license: Apache License 2.0
- Local override: `FACE_SFACE_MODEL`

Users deploying biometric recognition commercially should review the upstream model documentation and training-data provenance in addition to the code/model license. This repository does not grant rights beyond the upstream license terms.

## MiniFASNet anti-spoofing models

The Phase 4 passive RGB liveness gate uses the lightweight ONNX exports maintained by `yakhyo/face-anti-spoofing`, which is based on Minivision AI's Silent-Face-Anti-Spoofing project. The upstream repository is licensed under Apache License 2.0.

### MiniFASNetV2

- Runtime file: `MiniFASNetV2.onnx`
- Upstream release: `yakhyo/face-anti-spoofing` weights release
- SHA-256: `b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907`
- Expected size: `1743581` bytes
- Crop scale: `2.7`
- Local override: `FACE_LIVENESS_V2_MODEL`

### MiniFASNetV1SE

- Runtime file: `MiniFASNetV1SE.onnx`
- Upstream release: `yakhyo/face-anti-spoofing` weights release
- SHA-256: `ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676`
- Expected size: `1742335` bytes
- Crop scale: `4.0`
- Local override: `FACE_LIVENESS_V1SE_MODEL`

The MiniFAS inference convention used by this project follows the upstream implementation: 80×80 BGR crops, class index `1` as the real/live class, and ensemble averaging across the V2 and V1SE models.

## Security scope

MiniFAS provides passive RGB presentation-attack detection intended to reduce common attacks such as printed photographs and screen replays. It is not represented here as certified ISO/IEC 30107-3 presentation-attack detection and does not provide the guarantees of dedicated depth, infrared, or other specialized biometric sensors.

## Updating model pins

Any model update must update all of the following together:

1. download source;
2. expected byte size;
3. SHA-256 digest;
4. applicable upstream license/notice;
5. deterministic regression tests.

Do not replace a pin with a mutable `main`, `master`, or `latest` artifact without an integrity check.
