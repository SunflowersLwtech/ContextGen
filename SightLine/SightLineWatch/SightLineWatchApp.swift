//
//  SightLineWatchApp.swift
//  SightLineWatch
//
//  watchOS Companion App for SightLine.
//  Sole purpose: real-time heart rate capture via HKWorkoutSession
//  and transmission to iPhone via WCSession (<1s latency).
//
//  This replaces the HealthKit system sync path (10-20 min delay)
//  for PANIC detection (>120 BPM → force LOD 1).
//

import SwiftUI

@main
struct SightLineWatchApp: App {
    @StateObject private var workoutManager = WorkoutManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(workoutManager)
                .onAppear {
                    PhoneConnector.shared.activate()
                }
        }
    }
}
