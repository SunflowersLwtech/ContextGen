# iOS-Backend Protocol Alignment Matrix

This matrix tracks what iOS sends versus what the backend actually consumes.
Status values:
- `aligned`: payload and behavior are consistent.
- `fixed`: previously mismatched, now aligned by code changes.
- `no-op`: accepted by backend but intentionally ignored.

## WebSocket Upstream

| Action | iOS payload | Backend consumption | Status | Notes |
|---|---|---|---|---|
| audio (binary) | magic `0x01` + PCM bytes | `_MAGIC_AUDIO` branch in `server.py` | aligned | Primary fast path |
| image (binary) | magic `0x02` + JPEG bytes | `_MAGIC_IMAGE` branch in `server.py` | aligned | Primary fast path |
| audio (legacy json) | `{"type":"audio","data":"<base64>"}` | `message["data"]` decoded in `server.py` | aligned | Backward compatibility |
| image (legacy json) | `{"type":"image","data":"<base64>","mimeType":"image/jpeg"}` | `message["data"]`, optional `mimeType` | aligned | Backward compatibility |
| telemetry | `{"type":"telemetry","data":{...}}` | `parse_telemetry_to_ephemeral()` | aligned | Now includes `device_type` from iOS |
| gesture: lod_up/down | `{"type":"gesture","gesture":"lod_up|lod_down"}` | LOD re-decision in gesture branch | aligned | Immediate LOD override |
| gesture: mute_toggle | `{"type":"gesture","gesture":"mute_toggle","muted":bool}` | Reads explicit `muted` or toggles legacy payload | fixed | Removed state ambiguity |
| gesture: interrupt | `{"type":"gesture","gesture":"interrupt"}` | Sends interrupt content to Live API | aligned | |
| gesture: repeat_last | `{"type":"gesture","gesture":"repeat_last"}` | Replays last agent transcript | aligned | |
| gesture: sos | `{"type":"gesture","gesture":"sos"}` | Sets panic and calls panic handler | aligned | |
| gesture: emergency_pause | `{"type":"gesture","gesture":"emergency_pause","paused":bool}` | Reads `paused`, forces/resumes LOD | aligned | |
| camera_failure | `{"type":"camera_failure","error":"...","reason":"..."}` | Reads `error` then `reason` fallback | fixed | Backward + forward compatible |
| reload_face_library | `{"type":"reload_face_library"}` | Reloads user face library | aligned | |
| clear_face_library | `{"type":"clear_face_library"}` | Clears user face library | aligned | |
| activity_start | `{"type":"activity_start"}` | Forwarded to LiveRequestQueue + emits `debug_activity` + updates session activity state | fixed | Keep native VAD as primary path; explicit signal retained for observability/compat |
| activity_end | `{"type":"activity_end"}` | Forwarded to LiveRequestQueue + emits `debug_activity` + updates session activity state | fixed | Keep native VAD as primary path; explicit signal retained for observability/compat |

## REST API

| API | iOS payload/usage | Backend handling | Status | Notes |
|---|---|---|---|---|
| `POST /api/face/register` | `user_id`, `person_name`, `relationship`, `image_base64`, `photo_index`, `consent_confirmed`, `store_reference_photo` | Same fields consumed in `api_register_face` | aligned | |
| `GET /api/face/list/{user_id}` | list registered faces | returns `faces[]` | aligned | |
| `DELETE /api/face/{user_id}/{face_id}` | delete one face | deletes by path params | aligned | |
| `GET /api/profile/{user_id}` | loads profile JSON | reads Firestore document | aligned | |
| `POST /api/profile/{user_id}` | saves profile fields including `verbosity_preference` (`concise|detailed`) | field whitelist merge to Firestore | aligned | LOD now maps `concise` as low-verbosity |

## LOD-Specific Semantic Alignment

| Input | Before | Now |
|---|---|---|
| `verbosity_preference=\"concise\"` | No Rule-5 effect (treated as unknown value) | Treated as low-verbosity preference (`Rule5:concise_pref→-1`) |
| telemetry `device_type` | Backend expected it but iOS omitted it | iOS sends `device_type` (`phone_only` or `phone_and_watch`) |

## Runtime Validation Snapshot

- Cloud Run service: `sightline-backend` (region `us-central1`) is active.
- Latest tested revision path reports normal WS sessions and LOD transition logs.
- No observed `Unknown upstream message type` warnings in sampled recent logs.
