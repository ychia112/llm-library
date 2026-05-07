import Foundation
import SwiftUI

@MainActor
@Observable
class AppViewModel {
    var recentSessions: [Session] = []
    private let apiClient = APIClient.shared

    func loadRecent() async {
        do {
            let overview = try await apiClient.fetchOverview()
            self.recentSessions = Array(overview.recentSessions.prefix(5))
        } catch {
            print("Failed to load recent sessions: \(error)")
        }
    }
}
