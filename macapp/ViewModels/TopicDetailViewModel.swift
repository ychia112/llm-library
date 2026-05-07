import Foundation
import SwiftUI

@MainActor
@Observable
class TopicDetailViewModel {
    var allSessions: [Session] = []
    var selectedTags: Set<String> = []
    var isLoading: Bool = false

    private let apiClient = APIClient.shared

    var filteredSessions: [Session] {
        if selectedTags.isEmpty { return allSessions }
        return allSessions.filter { !selectedTags.isDisjoint(with: Set($0.tags)) }
    }

    func load(topic: String) async {
        isLoading = true
        do {
            allSessions = try await apiClient.fetchSessions(topic: topic)
        } catch {
            print("Failed to load topic sessions: \(error)")
            allSessions = []
        }
        isLoading = false
    }

    func toggleTag(_ tag: String) {
        if selectedTags.contains(tag) {
            selectedTags.remove(tag)
        } else {
            selectedTags.insert(tag)
        }
    }
}
