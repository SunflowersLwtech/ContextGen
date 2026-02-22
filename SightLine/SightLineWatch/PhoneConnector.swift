//
//  PhoneConnector.swift
//  SightLineWatch
//
//  Manages WCSession from watchOS → iPhone for real-time heart rate delivery.
//  Uses sendMessage when iPhone is reachable (<1s), falls back to
//  transferUserInfo when unreachable (queued for later delivery).
//

import WatchConnectivity
import Foundation
import Combine
import os

class PhoneConnector: NSObject, ObservableObject {
    static let shared = PhoneConnector()

    @Published var isReachable: Bool = false

    private static let logger = Logger(
        subsystem: "com.sightline.watch",
        category: "PhoneConnector"
    )

    private override init() {
        super.init()
    }

    // MARK: - Activation

    /// Activate WCSession. Must be called once at app launch.
    func activate() {
        guard WCSession.isSupported() else {
            Self.logger.warning("WCSession not supported on this device")
            return
        }

        WCSession.default.delegate = self
        WCSession.default.activate()
        Self.logger.info("WCSession activation requested")
    }

    // MARK: - Send Heart Rate

    /// Send heart rate to iPhone.
    /// - Parameters:
    ///   - bpm: Heart rate in beats per minute. 0 means monitoring stopped.
    ///   - isMonitoring: Whether the workout session is actively monitoring.
    func sendHeartRate(_ bpm: Double, isMonitoring: Bool = true) {
        let payload: [String: Any] = [
            "heartRate": bpm,
            "ts": Date().timeIntervalSince1970,
            "isMonitoring": isMonitoring,
        ]

        guard WCSession.default.activationState == .activated else {
            Self.logger.warning("WCSession not activated, dropping heart rate")
            return
        }

        if WCSession.default.isReachable {
            // Real-time path: sendMessage (<1s delivery)
            WCSession.default.sendMessage(
                payload,
                replyHandler: nil
            ) { error in
                Self.logger.error("sendMessage failed: \(error.localizedDescription)")
                // Fallback to transferUserInfo on failure
                WCSession.default.transferUserInfo(payload)
            }
        } else {
            // Offline path: transferUserInfo (queued, delivered when reachable)
            WCSession.default.transferUserInfo(payload)
            Self.logger.debug("iPhone unreachable — queued via transferUserInfo")
        }
    }
}

// MARK: - WCSessionDelegate

extension PhoneConnector: WCSessionDelegate {
    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        if let error = error {
            Self.logger.error("WCSession activation failed: \(error.localizedDescription)")
            return
        }

        Self.logger.info("WCSession activated: state=\(activationState.rawValue)")

        DispatchQueue.main.async { [weak self] in
            self?.isReachable = session.isReachable
        }
    }

    nonisolated func sessionReachabilityDidChange(_ session: WCSession) {
        let reachable = session.isReachable
        Self.logger.info("iPhone reachability changed: \(reachable)")

        DispatchQueue.main.async { [weak self] in
            self?.isReachable = reachable
        }
    }

    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {
        Self.logger.info("WCSession became inactive")
    }

    nonisolated func sessionDidDeactivate(_ session: WCSession) {
        Self.logger.info("WCSession deactivated, reactivating")
        WCSession.default.activate()
    }
}
