//
//  MessageProtocol.swift
//  SightLine
//
//  Defines the WebSocket message protocol for communication with the backend.
//  Upstream = iOS -> Server, Downstream = Server -> iOS.
//

import Foundation

// MARK: - Upstream Messages (iOS -> Server)

enum UpstreamMessage {
    case audio(data: Data)                         // PCM 16kHz mono
    case image(data: Data, mimeType: String)       // JPEG 768x768
    case telemetry(data: TelemetryData)
    case activityStart
    case activityEnd

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
        }
    }
}

// MARK: - Downstream Messages (Server -> iOS)

enum DownstreamMessage {
    case audio(data: Data)                          // PCM 24kHz
    case transcript(text: String, role: String)     // "user" or "agent"
    case lodUpdate(lod: Int)
    case goAway(retryMs: Int)
    case sessionResumption(handle: String)
    case sessionReady                               // Gemini Live API ready
    case unknown(raw: String)

    static func parse(text: String) -> DownstreamMessage? {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            return .unknown(raw: text)
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
