//
//  AppDelegate.swift
//  SightLine
//
//  Handles app-level setup: audio session configuration and
//  keeping the screen on (critical for blind users who cannot
//  easily re-activate a locked device).
//

import UIKit
import AVFoundation

class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Configure audio session for simultaneous capture and playback
        do {
            try AudioSessionManager.shared.configure()
        } catch {
            print("[SightLine] Audio session configuration failed: \(error)")
        }

        // Keep screen on - critical for blind users who rely on continuous camera feed
        application.isIdleTimerDisabled = true

        return true
    }
}
