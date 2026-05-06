import Foundation
import SwiftUI

@MainActor
@Observable
class SearchViewModel {
    var query: String = ""
    var results: [SearchResult] = []
    var hitType: String = ""
    var isLoading: Bool = false
    var errorMessage: String?
    
    private let apiClient = APIClient.shared
    
    func performSearch() async {
        guard !query.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let response = try await apiClient.search(query: query)
            self.results = response.results
            self.hitType = response.hitType
        } catch {
            self.errorMessage = error.localizedDescription
            self.results = []
            self.hitType = ""
        }
        
        isLoading = false
    }
}
