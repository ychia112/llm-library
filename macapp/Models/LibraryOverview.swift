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

struct TopicSummary: Codable, Identifiable, Hashable {
    var id: String { topic }
    let topic: String
    let count: Int
    let topTags: [String]
    
    enum CodingKeys: String, CodingKey {
        case topic, count
        case topTags = "top_tags"
    }
}

struct QuestionTypeStats: Codable, Identifiable {
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
