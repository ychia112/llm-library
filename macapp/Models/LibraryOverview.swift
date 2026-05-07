import Foundation

struct LibraryOverview: Codable {
    let totalSessions: Int
    let byTopic: [TopicSummary]
    let byQuestionType: [QuestionTypeStats]
    let byPlatform: [PlatformStats]
    let topTags: [TagStats]
    let recentSessions: [Session]
    
    enum CodingKeys: String, CodingKey {
        case totalSessions = "total_sessions"
        case byTopic = "by_topic"
        case byQuestionType = "by_question_type"
        case byPlatform = "by_platform"
        case topTags = "top_tags"
        case recentSessions = "recent_sessions"
    }
}

struct TopicSummary: Identifiable, Hashable {
    var id: String { topic }
    let topic: String
    let count: Int
    let topTags: [String]
    let byQuestionType: [QuestionTypeStats]
    let topEntities: [String]
}

extension TopicSummary: Codable {
    enum CodingKeys: String, CodingKey {
        case topic, count
        case topTags = "top_tags"
        case byQuestionType = "by_question_type"
        case topEntities = "top_entities"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        topic = try c.decode(String.self, forKey: .topic)
        count = try c.decode(Int.self, forKey: .count)
        topTags = try c.decodeIfPresent([String].self, forKey: .topTags) ?? []
        byQuestionType = try c.decodeIfPresent([QuestionTypeStats].self, forKey: .byQuestionType) ?? []
        topEntities = try c.decodeIfPresent([String].self, forKey: .topEntities) ?? []
    }
}

struct QuestionTypeStats: Codable, Identifiable, Hashable {
    var id: String { questionType }
    let questionType: String
    let count: Int

    enum CodingKeys: String, CodingKey {
        case questionType = "question_type"
        case count
    }
}

struct PlatformStats: Codable, Identifiable {
    var id: String { platform }
    let platform: String
    let count: Int
}

struct TagStats: Codable, Identifiable {
    var id: String { tag }
    let tag: String
    let count: Int
}
