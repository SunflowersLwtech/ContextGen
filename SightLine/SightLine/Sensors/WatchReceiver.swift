//
//  WatchReceiver.swift
//  SightLine
//
//  Receives real-time heart rate data from the watchOS Companion App
//  via WCSession. This is the PRIMARY heart rate channel (<1s latency).
//  HealthKitManager serves as backup (10-20 min system sync delay).
//
//  Data flow:
//    Apple Watch (WorkoutManager) → WCSession.sendMessage
//    → WatchReceiver.didReceiveMessage → SensorManager.heartRate
//    → TelemetryAggregator → WebSocket → Cloud Run → LOD Engine
//

import WatchConnectivity
import Foundation
import Combine
import os

class WatchReceiver: NSObject, ObservableObject {
    /// Real-time heart rate from Apple Watch via WCSession.
    /// nil when no watch data has been received.
    @Published var heartRate: Double? = nil

    /// Whether the Apple Watch is reachable via WCSession.
    @Published var isWatchReachable: Bool = false

    /// Whether the watch is actively monitoring (workout session running).
    @Published var isWatchMonitoring: Bool = false

    /// Timestamp of the last received heart rate sample.
    @Published var lastUpdateTime: Date? = nil

    private static let logger = Logger(
        subsystem: "com.sightline.app",
        category: "WatchReceiver"
    )

    /// Timeout after which watch heart rate is considered stale (30 seconds).
    private let staleThreshold: TimeInterval = 30.0

    // MARK: - Activation

    /// Activate WCSession on the iPhone side. Must be called once at app launch.
    func activate() {
        guard WCSession.isSupported() else {
            Self.logger.info("WCSession not supported (no paired Apple Watch)")
            return
        }

        WCSession.default.delegate = self
        WCSession.default.activate()
        Self.logger.info("WCSession activation requested (iPhone side)")
    }

    // MARK: - Heart Rate Access

    /// Returns the real-time watch heart rate if fresh (within staleThreshold),
    /// otherwise nil (caller should fall back to HealthKit).
    var freshHeartRate: Double? {
        guard let hr = heartRate, hr > 0,
              let lastUpdate = lastUpdateTime,
              Date().timeIntervalSince(lastUpdate) < staleThreshold else {
            return nil
        }
        return hr
    }

    // MARK: - Private

    private func processHeartRateMessage(_ message: [String: Any]) {
        guard let bpm = message["heartRate"] as? Double else { return }

        let isMonitoring = message["isMonitoring"] as? Bool ?? true
        let timestamp = message["ts"] as? TimeInterval

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }

            if isMonitoring && bpm > 0 {
                self.heartRate = bpm
                self.lastUpdateTime = timestamp.map { Date(timeIntervalSince1970: $0) } ?? Date()
                self.isWatchMonitoring = true
            } else {
                // Monitoring stopped (bpm = 0 or isMonitoring = false)
                self.isWatchMonitoring = false
                self.heartRate = nil
                self.lastUpdateTime = nil
            }
        }

        if isMonitoring && bpm > 0 {
            Self.logger.debug("Watch HR received: \(Int(bpm)) BPM")
        } else {
            Self.logger.info("Watch monitoring stopped")
        }
    }
}

// MARK: - WCSessionDelegate

extension WatchReceiver: WCSessionDelegate {

    // Required: activation completion
    func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        if let error = error {
            Self.logger.error("WCSession activation failed: \(error.localizedDescription)")
            return
        }

        Self.logger.info(
            "WCSession activated: state=\(activationState.rawValue), paired=\(session.isPaired), installed=\(session.isWatchAppInstalled)"
        )

        DispatchQueue.main.async { [weak self] in
            self?.isWatchReachable = session.isReachable
        }
    }

    // Required on iOS: session became inactive (watch switching)
    func sessionDidBecomeInactive(_ session: WCSession) {
        Self.logger.info("WCSession became inactive")
    }

    // Required on iOS: session deactivated (re-activate for new watch)
    func sessionDidDeactivate(_ session: WCSession) {
        Self.logger.info("WCSession deactivated — re-activating")
        WCSession.default.activate()
    }

    // Real-time message from watch (sendMessage path, <1s)
    func session(
        _ session: WCSession,
        didReceiveMessage message: [String: Any]
    ) {
        processHeartRateMessage(message)
    }

    // Queued transfer from watch (transferUserInfo path, delayed)
    func session(
        _ session: WCSession,
        didReceiveUserInfo userInfo: [String: Any] = [:]
    ) {
        processHeartRateMessage(userInfo)
    }

    // Reachability changed
    func sessionReachabilityDidChange(_ session: WCSession) {
        let reachable = session.isReachable
        Self.logger.info("Watch reachability changed: \(reachable)")

        DispatchQueue.main.async { [weak self] in
            self?.isWatchReachable = reachable
        }
    }
}
