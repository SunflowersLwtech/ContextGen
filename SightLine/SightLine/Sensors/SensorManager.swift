//
//  SensorManager.swift
//  SightLine
//
//  Unified sensor interface that aggregates data from all sub-sensors
//  (Motion, Location, NoiseMeter, HealthKit) into a TelemetryData snapshot.
//  Provides @Published properties for SwiftUI binding.
//

import Foundation
import Combine
import os

class SensorManager: ObservableObject {
    @Published var currentTelemetry = TelemetryData()
    @Published var isCollecting = false

    private static let logger = Logger(subsystem: "com.sightline.app", category: "Sensors")

    let motionManager = MotionManager()
    let locationManager = LocationManager()
    let noiseMeter = NoiseMeter()
    let healthKitManager = HealthKitManager()

    private var cancellables = Set<AnyCancellable>()

    init() {
        observeSubSensors()
    }

    /// Start all sensor collection.
    func startAll() {
        guard !isCollecting else { return }
        isCollecting = true
        motionManager.startMonitoring()
        locationManager.startMonitoring()

        // HealthKit needs async authorization
        Task {
            await healthKitManager.requestAuthorization()
            healthKitManager.startMonitoring()
        }

        Self.logger.info("All sensors started")
    }

    /// Stop all sensor collection.
    func stopAll() {
        guard isCollecting else { return }
        isCollecting = false
        motionManager.stopMonitoring()
        locationManager.stopMonitoring()
        healthKitManager.stopMonitoring()
        noiseMeter.reset()
        Self.logger.info("All sensors stopped")
    }

    /// Provide RMS callback for AudioCaptureManager to feed NoiseMeter.
    /// Wire this to AudioCaptureManager.onAudioLevelUpdate in the pipeline.
    func processAudioRMS(_ rms: Float) {
        noiseMeter.processRMS(rms)
    }

    /// Get a snapshot of current aggregated telemetry data.
    func snapshot() -> TelemetryData {
        var data = TelemetryData()

        data.motionState = motionManager.motionState
        data.stepCadence = Int(motionManager.stepCadence)
        data.ambientNoiseDb = noiseMeter.ambientNoiseDb

        if locationManager.latitude != 0 || locationManager.longitude != 0 {
            data.gps = GPSData(
                lat: locationManager.latitude,
                lng: locationManager.longitude,
                accuracy: locationManager.accuracy,
                speed: locationManager.speed,
                altitude: locationManager.altitude
            )
        }

        if locationManager.heading != 0 {
            data.heading = locationManager.heading
        }

        data.timeContext = Self.currentTimeContext()
        data.heartRate = healthKitManager.heartRate
        data.panic = false

        return data
    }

    // MARK: - Private

    /// Observe sub-sensor changes and update currentTelemetry.
    private func observeSubSensors() {
        // Combine all sensor publishers to update the aggregate
        Publishers.CombineLatest4(
            motionManager.$motionState,
            motionManager.$stepCadence,
            noiseMeter.$ambientNoiseDb,
            healthKitManager.$heartRate
        )
        .receive(on: DispatchQueue.main)
        .sink { [weak self] _, _, _, _ in
            self?.currentTelemetry = self?.snapshot() ?? TelemetryData()
        }
        .store(in: &cancellables)
    }

    /// Derive time context from current hour.
    private static func currentTimeContext() -> String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 6..<10: return "morning_commute"
        case 10..<17: return "work_hours"
        case 17..<21: return "evening"
        case 21..<24, 0..<6: return "late_night"
        default: return "unknown"
        }
    }
}
