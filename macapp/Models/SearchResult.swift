import Foundation

struct SearchResult: Codable, Identifiable {
    var id: String { session.id }
    let session: Session
    let similarity: Double
}

struct SearchResponse: Codable {
    let results: [SearchResult]
    let hitType: String
    
    enum CodingKeys: String, CodingKey {
        case results
        case hitType = "hit_type"
    }
}
