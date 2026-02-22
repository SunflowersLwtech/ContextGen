//
//  WorkoutManager.swift
//  SightLineWatch
//
//  Manages HKWorkoutSession for continuous heart rate capture.
//  When a workout is active, Apple Watch samples heart rate every 1-5 seconds
//  (vs. 5-15 minutes at rest). Each new reading is forwarded to iPhone
//  via PhoneConnector (WCSession) for real-time PANIC detection.
//
//  Reference: Apple SpeedySloth sample, trimmed to heart-rate-only.
//

import HealthKit
import Foundation
import Combine
import os

class WorkoutManager: NSObject, ObservableObject {
    // MARK: - Published State

    @Published var heartRate: Double = 0
    @Published var isRunning: Bool = false
    @Published var isAuthorized: Bool = false

    // MARK: - Private

    private static let logger = Logger(
        subsystem: "com.sightline.watch",
        category: "Workout"
    )

    private let healthStore = HKHealthStore()
    private var session: HKWorkoutSession?
    private var builder: HKLiveWorkoutBuilder?

    // MARK: - Authorization

    /// Request HealthKit read permission for heart rate.
    func requestAuthorization() async {
        let heartRateType = HKQuantityType(.heartRate)

        do {
            try await healthStore.requestAuthorization(toShare: [.workoutType()], read: [heartRateType])
            await MainActor.run {
                isAuthorized = true
            }
            Self.logger.info("HealthKit authorization granted")
        } catch {
            Self.logger.error("HealthKit authorization failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Workout Lifecycle

    /// Start a workout session to enable high-frequency heart rate sampling.
    func startWorkout() {
        guard !isRunning else { return }

        Task {
            if !isAuthorized {
                await requestAuthorization()
            }

            await _startWorkoutSession()
        }
    }

    /// Stop the active workout session.
    func stopWorkout() {
        guard isRunning else { return }

        session?.end()

        builder?.endCollection(withEnd: Date()) { [weak self] success, error in
            if let error = error {
                Self.logger.error("End collection failed: \(error.localizedDescription)")
            }

            self?.builder?.finishWorkout { workout, error in
                if let error = error {
                    Self.logger.error("Finish workout failed: \(error.localizedDescription)")
                }
                Self.logger.info("Workout finished successfully")
            }
        }

        isRunning = false

        // Notify iPhone that monitoring stopped
        PhoneConnector.shared.sendHeartRate(0, isMonitoring: false)

        Self.logger.info("Workout stopped")
    }

    // MARK: - Private

    private func _startWorkoutSession() async {
        let config = HKWorkoutConfiguration()
        config.activityType = .other          // Generic activity — just need HR
        config.locationType = .outdoor        // Outdoor enables GPS if needed

        do {
            session = try HKWorkoutSession(
                healthStore: healthStore,
                configuration: config
            )
            builder = session?.associatedWorkoutBuilder()

            session?.delegate = self
            builder?.delegate = self

            builder?.dataSource = HKLiveWorkoutDataSource(
                healthStore: healthStore,
                workoutConfiguration: config
            )

            let startDate = Date()
            session?.startActivity(with: startDate)

            try await builder?.beginCollection(at: startDate)

            await MainActor.run {
                isRunning = true
            }

            Self.logger.info("Workout session started — high-frequency HR active")
        } catch {
            Self.logger.error("Failed to start workout: \(error.localizedDescription)")
        }
    }

    /// Extract latest heart rate from workout builder statistics.
    private func updateHeartRate(from builder: HKLiveWorkoutBuilder) {
        let heartRateType = HKQuantityType(.heartRate)

        guard let statistics = builder.statistics(for: heartRateType),
              let quantity = statistics.mostRecentQuantity() else {
            return
        }

        let bpm = quantity.doubleValue(
            for: HKUnit.count().unitDivided(by: .minute())
        )

        guard bpm > 0 else { return }

        DispatchQueue.main.async { [weak self] in
            self?.heartRate = bpm
        }

        // Forward to iPhone via WCSession (<1s latency)
        PhoneConnector.shared.sendHeartRate(bpm, isMonitoring: true)

        Self.logger.debug("Heart rate: \(Int(bpm)) BPM → sent to iPhone")
    }
}

// MARK: - HKWorkoutSessionDelegate

extension WorkoutManager: HKWorkoutSessionDelegate {
    nonisolated func workoutSession(
        _ workoutSession: HKWorkoutSession,
        didChangeTo toState: HKWorkoutSessionState,
        from fromState: HKWorkoutSessionState,
        date: Date
    ) {
        Self.logger.info("Workout state: \(fromState.rawValue) → \(toState.rawValue)")

        if toState == .ended {
            DispatchQueue.main.async { [weak self] in
                self?.isRunning = false
            }
        }
    }

    nonisolated func workoutSession(
        _ workoutSession: HKWorkoutSession,
        didFailWithError error: Error
    ) {
        Self.logger.error("Workout session failed: \(error.localizedDescription)")

        DispatchQueue.main.async { [weak self] in
            self?.isRunning = false
        }
    }
}

// MARK: - HKLiveWorkoutBuilderDelegate

extension WorkoutManager: HKLiveWorkoutBuilderDelegate {
    nonisolated func workoutBuilder(
        _ workoutBuilder: HKLiveWorkoutBuilder,
        didCollectDataOf collectedTypes: Set<HKSampleType>
    ) {
        for type in collectedTypes {
            guard let quantityType = type as? HKQuantityType,
                  quantityType == HKQuantityType(.heartRate) else {
                continue
            }

            // Must dispatch to MainActor for @Published updates
            DispatchQueue.main.async { [weak self] in
                self?.updateHeartRate(from: workoutBuilder)
            }
        }
    }

    nonisolated func workoutBuilderDidCollectEvent(
        _ workoutBuilder: HKLiveWorkoutBuilder
    ) {
        // Not used — we only care about heart rate data
    }
}
