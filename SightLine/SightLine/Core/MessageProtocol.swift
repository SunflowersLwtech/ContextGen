//
//  MessageProtocol.swift
//  SightLine
//
//  Defines the WebSocket message protocol for communication with the backend.
//  Upstream = iOS -> Server, Downstream = Server -> iOS.
//

import Foundation

// MARK: - Upstream Messages (iOS -> Server)

/// Magic bytes for binary WebSocket protocol.
/// Eliminates ~33% Base64 overhead on audio/image payloads.
enum BinaryMagic {
    static let audio: UInt8 = 0x01   // PCM 16kHz mono
    static let image: UInt8 = 0x02   // JPEG 768x768
}

enum UpstreamMessage {
    case audio(data: Data)                         // PCM 16kHz mono
    case image(data: Data, mimeType: String)       // JPEG 768x768
    case telemetry(data: TelemetryData)
    case activityStart
    case activityEnd
    case gesture(type: String)

    /// Encode as optimized binary frame (magic byte + raw payload).
    /// Returns nil for message types that must be sent as JSON text.
    func toBinary() -> Data? {
        switch self {
        case .audio(let data):
            var frame = Data(capacity: 1 + data.count)
            frame.append(BinaryMagic.audio)
            frame.append(data)
            return frame
        case .image(let data, _):
            var frame = Data(capacity: 1 + data.count)
            frame.append(BinaryMagic.image)
            frame.append(data)
            return frame
        default:
            return nil  // Non-binary types use JSON
        }
    }

    /// Legacy JSON encoding (for telemetry, gestures, control messages).
    func toJSON() -> String {
        switch self {
        case .audio(let data):
            return "{\"type\":\"audio\",\"data\":\"\(data.base64EncodedString())\"}"
        case .image(let data, let mimeType):
            return "{\"type\":\"image\",\"data\":\"\(data.base64EncodedString())\",\"mimeType\":\"\(mimeType)\"}"
        case .telemetry(let data):
            let jsonData = try! JSONEncoder().encode(data)
            let jsonStr = String(data: jsonData, encoding: .utf8)!
            return "{\"type\":\"telemetry\",\"data\":\(jsonStr)}"
        case .activityStart:
            return "{\"type\":\"activity_start\"}"
        case .activityEnd:
            return "{\"type\":\"activity_end\"}"
        case .gesture(let type):
            return "{\"type\":\"gesture\",\"gesture\":\"\(type)\"}"
        }
    }
}

// MARK: - Downstream Messages (Server -> iOS)

enum ToolBehaviorMode: String {
    case INTERRUPT
    case WHEN_IDLE
    case SILENT

    static func parse(from json: [String: Any]) -> ToolBehaviorMode {
        if let behavior = json["behavior"] as? String,
           let mode = ToolBehaviorMode(rawValue: behavior.uppercased()) {
            return mode
        }
        if let data = json["data"] as? [String: Any],
           let behavior = data["behavior"] as? String,
           let mode = ToolBehaviorMode(rawValue: behavior.uppercased()) {
            return mode
        }
        return .WHEN_IDLE
    }
}

enum DownstreamMessage {
    case audio(data: Data)                          // PCM 24kHz
    case transcript(text: String, role: String)     // "user" or "agent"
    case lodUpdate(lod: Int)
    case goAway(retryMs: Int)
    case sessionResumption(handle: String)
    case sessionReady                               // Gemini Live API ready
    case toolEvent(tool: String, behavior: ToolBehaviorMode, payload: [String: Any])
    case visionResult(summary: String, behavior: ToolBehaviorMode)
    case ocrResult(summary: String, behavior: ToolBehaviorMode)
    case navigationResult(summary: String, behavior: ToolBehaviorMode)
    case searchResult(summary: String, behavior: ToolBehaviorMode)
    case personIdentified(name: String, behavior: ToolBehaviorMode)
    case identityUpdate(name: String, matched: Bool, behavior: ToolBehaviorMode)
    case capabilityDegraded(capability: String, reason: String, recoverable: Bool)
    case debugLod(data: [String: Any])
    case panic(message: String)
    case interrupted
    case unknown(raw: String)

    static func parse(text: String) -> DownstreamMessage? {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            return .unknown(raw: text)
        }

        let behavior = ToolBehaviorMode.parse(from: json)
        let dataPayload = json["data"] as? [String: Any] ?? [:]

        func extractSummary() -> String {
            if let summary = json["summary"] as? String, !summary.isEmpty {
                return summary
            }
            if let summary = dataPayload["summary"] as? String, !summary.isEmpty {
                return summary
            }
            if let text = dataPayload["text"] as? String, !text.isEmpty {
                return text
            }
            return ""
        }

        func extractPersonName() -> String {
            if let name = json["person_name"] as? String, !name.isEmpty {
                return name
            }
            if let name = dataPayload["person_name"] as? String, !name.isEmpty {
                return name
            }
            if let name = json["name"] as? String, !name.isEmpty {
                return name
            }
            return "unknown"
        }

        switch type {
        case "transcript":
            let text = json["text"] as? String ?? ""
            let role = json["role"] as? String ?? "agent"
            return .transcript(text: text, role: role)
        case "lod_update":
            let lod = json["lod"] as? Int ?? 2
            return .lodUpdate(lod: lod)
        case "go_away":
            let retryMs = json["retry_ms"] as? Int ?? 500
            return .goAway(retryMs: retryMs)
        case "session_resumption":
            let handle = json["handle"] as? String ?? ""
            return .sessionResumption(handle: handle)
        case "session_ready":
            return .sessionReady
        case "tool_event", "tool_result", "tool_status":
            let tool = (json["tool"] as? String)
                ?? (json["name"] as? String)
                ?? (dataPayload["tool"] as? String)
                ?? "unknown_tool"
            return .toolEvent(tool: tool, behavior: behavior, payload: dataPayload)
        case "vision_result":
            return .visionResult(summary: extractSummary(), behavior: behavior)
        case "ocr_result":
            return .ocrResult(summary: extractSummary(), behavior: behavior)
        case "navigation_result", "navigate_result":
            return .navigationResult(summary: extractSummary(), behavior: behavior)
        case "search_result", "grounding_result":
            return .searchResult(summary: extractSummary(), behavior: behavior)
        case "person_identified":
            return .personIdentified(name: extractPersonName(), behavior: behavior)
        case "identity_update":
            let matched = (json["matched"] as? Bool)
                ?? (dataPayload["matched"] as? Bool)
                ?? false
            return .identityUpdate(name: extractPersonName(), matched: matched, behavior: behavior)
        case "capability_degraded":
            let capability = json["capability"] as? String ?? "unknown"
            let reason = json["reason"] as? String ?? ""
            let recoverable = json["recoverable"] as? Bool ?? true
            return .capabilityDegraded(capability: capability, reason: reason, recoverable: recoverable)
        case "debug_lod":
            let lodData = json["data"] as? [String: Any] ?? json
            return .debugLod(data: lodData)
        case "panic":
            let message = json["message"] as? String ?? "PANIC detected"
            return .panic(message: message)
        case "interrupted":
            return .interrupted
        default:
            return .unknown(raw: text)
        }
    }
}

// MARK: - Telemetry Data

struct TelemetryData: Codable {
    var motionState: String = "stationary"
    var stepCadence: Int = 0
    var ambientNoiseDb: Double = 50.0
    var gps: GPSData?
    var heading: Double?
    var timeContext: String = "unknown"
    var heartRate: Double?
    var userGesture: String?
    var panic: Bool = false

    enum CodingKeys: String, CodingKey {
        case motionState = "motion_state"
        case stepCadence = "step_cadence"
        case ambientNoiseDb = "ambient_noise_db"
        case gps
        case heading
        case timeContext = "time_context"
        case heartRate = "heart_rate"
        case userGesture = "user_gesture"
        case panic
    }
}

struct GPSData: Codable {
    var lat: Double
    var lng: Double
    var accuracy: Double?
    var speed: Double?
    var altitude: Double?

    enum CodingKeys: String, CodingKey {
        case lat = "latitude"
        case lng = "longitude"
        case accuracy
        case speed
        case altitude
    }
}
