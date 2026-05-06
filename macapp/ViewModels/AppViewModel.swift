import Foundation
import SwiftUI

@MainActor
@Observable
class AppViewModel {
    var selection: NavigationItem? = .search
    var selectedSessionID: String?
    var recentSessions: [Session] = []
    
    var apiClient = APIClient.shared
    
    func loadRecent() async {
        do {
            let overview = try await apiClient.fetchOverview()
            self.recentSessions = Array(overview.recentSessions.prefix(5))
        } catch {
            print("Failed to load recent sessions: \(error)")
        }
    }
}

enum NavigationItem: String, CaseIterable, Hashable {
    case search = "Search"
    case library = "Library"
    
    var icon: String {
        switch self {
        case .search: return "magnifyingglass"
        case .library: return "books.vertical"
        }
    }
}
