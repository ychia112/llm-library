import Foundation

struct Session: Codable, Identifiable, Hashable {
    let id: String
    let platform: String
    let title: String
    let topic: String?
    let tags: [String]
    let keyEntities: [String]
    let questionType: String?
    let summary: String?
    let createdAt: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, platform, title, topic, tags, summary
        case keyEntities = "key_entities"
        case questionType = "question_type"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct Message: Codable, Hashable, Identifiable {
    var id: UUID { UUID() }
    let role: String
    let content: String
}

struct SessionDetail: Codable, Identifiable {
    let id: String
    let platform: String
    let title: String
    let topic: String?
    let tags: [String]
    let keyEntities: [String]
    let questionType: String?
    let summary: String?
    let createdAt: String
    let updatedAt: String
    let messages: [Message]

    enum CodingKeys: String, CodingKey {
        case id, platform, title, topic, tags, summary, messages
        case keyEntities = "key_entities"
        case questionType = "question_type"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct PaginatedSessions: Codable {
    let sessions: [Session]
    let total: Int
}
