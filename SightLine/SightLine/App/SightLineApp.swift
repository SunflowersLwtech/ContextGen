//
//  SightLineApp.swift
//  SightLine
//
//  Main app entry point. Uses AppDelegate for audio session setup.
//

import SwiftUI

@main
struct SightLineApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            MainView()
        }
    }
}
