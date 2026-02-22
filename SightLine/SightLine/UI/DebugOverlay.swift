//
//  DebugOverlay.swift
//  SightLine
//
//  Transparent overlay showing LOD state, telemetry, latency, and sub-agent
//  status. Intended for demo judges to observe the system's internal decisions.
//
//  Toggle: triple-tap gesture on MainView, or always-on under #if DEBUG.
//  SL-77: Phase 4 – DebugOverlay for iOS.
//

import SwiftUI
import Combine
import os

private let logger = Logger(subsystem: "com.sightline.app", category: "DebugOverlay")

// MARK: - Debug Data Model

@MainActor
final class DebugOverlayModel: ObservableObject {
    @Published var currentLOD: Int = 2
    @Published var previousLOD: Int = 2
    @Published var lodReason: String = ""
    @Published var triggeredRules: [String] = []

    // Telemetry snapshot
    @Published var motionState: String = "unknown"
    @Published var heartRate: Double?
    @Published var noiseDb: Double = 50.0
    @Published var stepCadence: Double = 0.0

    // Connection
    @Published var isConnected: Bool = false
    @Published var isSafeMode: Bool = false

    // Sub-agent capabilities
    @Published var visionStatus: String = "ready"
    @Published var ocrStatus: String = "ready"
    @Published var faceStatus: String = "ready"

    // Memory Top 3 (SL-77)
    @Published var memoryTop3: [String] = []

    // Latency
    @Published var lastEventTime: Date?

    var latencyText: String {
        guard let t = lastEventTime else { return "--" }
        let ms = Int(Date().timeIntervalSince(t) * 1000)
        return "\(ms)ms"
    }

    func updateFromLodDebug(_ data: [String: Any]) {
        if let lod = data["lod"] as? Int { currentLOD = lod }
        if let prev = data["prev"] as? Int { previousLOD = prev }
        if let reason = data["reason"] as? String { lodReason = reason }
        if let rules = data["rules"] as? [String] { triggeredRules = rules }
        if let motion = data["motion"] as? String { motionState = motion }
        if let hr = data["hr"] as? Double { heartRate = hr }
        if let noise = data["noise_db"] as? Double { noiseDb = noise }
        if let cadence = data["cadence"] as? Double { stepCadence = cadence }
        if let memories = data["memory_top3"] as? [String] {
            memoryTop3 = memories
        }
        lastEventTime = Date()
    }

    func markCapabilityDegraded(_ capability: String) {
        switch capability {
        case "vision": visionStatus = "degraded"
        case "ocr": ocrStatus = "degraded"
        case "face": faceStatus = "degraded"
        default: break
        }
    }

    func markCapabilityReady(_ capability: String) {
        switch capability {
        case "vision": visionStatus = "ready"
        case "ocr": ocrStatus = "ready"
        case "face": faceStatus = "ready"
        default: break
        }
    }
}

// MARK: - Debug Overlay View

struct DebugOverlay: View {
    @ObservedObject var model: DebugOverlayModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // LOD header
            HStack(spacing: 8) {
                lodBadge
                Text(model.lodReason.isEmpty ? "Initializing..." : model.lodReason)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(.white.opacity(0.7))
                    .lineLimit(2)
            }

            Divider().background(Color.white.opacity(0.2))

            // Telemetry row
            HStack(spacing: 12) {
                label("Motion", value: model.motionState)
                label("Noise", value: String(format: "%.0fdB", model.noiseDb))
                if let hr = model.heartRate {
                    label("HR", value: String(format: "%.0f", hr))
                }
                label("Cadence", value: String(format: "%.0f", model.stepCadence))
            }

            // Sub-agent status row
            HStack(spacing: 12) {
                capabilityDot("Vision", status: model.visionStatus)
                capabilityDot("OCR", status: model.ocrStatus)
                capabilityDot("Face", status: model.faceStatus)
                Spacer()
                label("Latency", value: model.latencyText)
            }

            // Memory Top 3 (SL-77)
            if !model.memoryTop3.isEmpty {
                Divider().background(Color.white.opacity(0.2))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Memory Top 3")
                        .font(.system(size: 8, design: .monospaced))
                        .foregroundColor(.white.opacity(0.4))
                    ForEach(model.memoryTop3.prefix(3), id: \.self) { memory in
                        Text("• \(memory)")
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(.white.opacity(0.6))
                            .lineLimit(2)
                    }
                }
            }

            // Rules
            if !model.triggeredRules.isEmpty {
                Text(model.triggeredRules.joined(separator: " | "))
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.white.opacity(0.5))
                    .lineLimit(1)
            }

            // Connection
            HStack(spacing: 6) {
                Circle()
                    .fill(model.isSafeMode ? Color.red : (model.isConnected ? Color.green : Color.yellow))
                    .frame(width: 6, height: 6)
                Text(model.isSafeMode ? "SAFE MODE" : (model.isConnected ? "Connected" : "Disconnected"))
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.white.opacity(0.6))
            }
        }
        .padding(10)
        .background(Color.black.opacity(0.75))
        .cornerRadius(8)
        .padding(.horizontal, 12)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    // MARK: - Subviews

    private var lodBadge: some View {
        Text("LOD \(model.currentLOD)")
            .font(.system(size: 14, weight: .bold, design: .monospaced))
            .foregroundColor(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 2)
            .background(lodColor)
            .cornerRadius(4)
    }

    private var lodColor: Color {
        switch model.currentLOD {
        case 1: return .red
        case 2: return .orange
        case 3: return .green
        default: return .gray
        }
    }

    private func label(_ title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title)
                .font(.system(size: 8, design: .monospaced))
                .foregroundColor(.white.opacity(0.4))
            Text(value)
                .font(.system(size: 11, weight: .medium, design: .monospaced))
                .foregroundColor(.white.opacity(0.8))
        }
    }

    private func capabilityDot(_ name: String, status: String) -> some View {
        HStack(spacing: 3) {
            Circle()
                .fill(status == "ready" ? Color.green : Color.red)
                .frame(width: 5, height: 5)
            Text(name)
                .font(.system(size: 9, design: .monospaced))
                .foregroundColor(.white.opacity(0.6))
        }
    }
}
