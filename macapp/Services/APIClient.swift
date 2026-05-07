import Foundation
import SwiftUI

enum APIError: Error, LocalizedError {
    case connectionFailed(String)
    case invalidURL
    case invalidResponse
    case decodingFailed
    case serverError(String)
    
    var errorDescription: String? {
        switch self {
        case .connectionFailed(let details):
            return "無法連線到伺服器 (\(details))。請檢查 127.0.0.1:8765 是否正常，或 Xcode Sandbox 權限。"
        case .invalidURL: return "無效的 URL"
        case .invalidResponse: return "伺服器回應無效"
        case .decodingFailed: return "解析資料失敗"
        case .serverError(let msg): return "伺服器錯誤: \(msg)"
        }
    }
}

@MainActor
@Observable
class APIClient {
    let baseURL = "http://127.0.0.1:8765"
    var isConnected: Bool = false
    
    static let shared = APIClient()
    private init() {}
    
    private func request<T: Decodable>(path: String, method: String = "GET", body: Data? = nil) async throws -> T {
        guard let url = URL(string: baseURL + path) else { throw APIError.invalidURL }
        
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        // /ask 與 /ingest 可能需要較長時間（尤其是本地 Ollama 大模型）
        if path.hasPrefix("/ask") || path.hasPrefix("/ingest") {
            req.timeoutInterval = 120
        } else {
            req.timeoutInterval = 15
        }
        
        do {
            let (data, response) = try await URLSession.shared.data(for: req)
            guard let httpResponse = response as? HTTPURLResponse else { 
                print("DEBUG: Invalid response type")
                throw APIError.invalidResponse 
            }
            
            print("DEBUG: Response Code \(httpResponse.statusCode) for \(path)")
            
            if (200...299).contains(httpResponse.statusCode) {
                self.isConnected = true
                do {
                    return try JSONDecoder().decode(T.self, from: data)
                } catch {
                    print("DEBUG: DECODE ERROR -> \(error)")
                    if let raw = String(data: data, encoding: .utf8) {
                        print("DEBUG: RAW RESPONSE -> \(raw)")
                    }
                    throw APIError.decodingFailed
                }
            } else {
                throw APIError.serverError("Status \(httpResponse.statusCode)")
            }
        } catch let apiError as APIError {
            throw apiError
        } catch let urlError as URLError {
            self.isConnected = false
            print("DEBUG: URL ERROR -> \(urlError)")
            throw APIError.connectionFailed(urlError.localizedDescription)
        } catch {
            self.isConnected = false
            print("DEBUG: NETWORK ERROR -> \(error)")
            throw APIError.connectionFailed(error.localizedDescription)
        }
    }
    
    func fetchOverview() async throws -> LibraryOverview { return try await request(path: "/library/overview") }
    func fetchTopics() async throws -> [TopicSummary] { return try await request(path: "/library/topics") }
    func fetchSessions(tag: String? = nil, platform: String? = nil, questionType: String? = nil, topic: String? = nil) async throws -> [Session] {
        var components = URLComponents(string: baseURL + "/sessions")!
        var queryItems = [URLQueryItem]()
        if let tag, !tag.isEmpty { queryItems.append(URLQueryItem(name: "tag", value: tag)) }
        if let platform, !platform.isEmpty { queryItems.append(URLQueryItem(name: "platform", value: platform)) }
        if let questionType, !questionType.isEmpty { queryItems.append(URLQueryItem(name: "question_type", value: questionType)) }
        if let topic, !topic.isEmpty { queryItems.append(URLQueryItem(name: "topic", value: topic)) }
        components.queryItems = queryItems
        let fullPath = components.url!.absoluteString.replacingOccurrences(of: baseURL, with: "")
        let paginated: PaginatedSessions = try await request(path: fullPath)
        return paginated.sessions
    }
    func fetchSession(id: String) async throws -> SessionDetail { return try await request(path: "/sessions/\(id)") }
    func search(query: String, topK: Int = 5) async throws -> SearchResponse {
        let body = try? JSONSerialization.data(withJSONObject: ["query": query, "top_k": topK])
        return try await request(path: "/search", method: "POST", body: body)
    }
    func ask(query: String, platform: String? = nil, provider: String = "ollama") async throws -> AskResponse {
        var dict: [String: Any] = ["query": query, "provider": provider]
        if let platform { dict["platform"] = platform }
        let body = try? JSONSerialization.data(withJSONObject: dict)
        return try await request(path: "/ask", method: "POST", body: body)
    }
    func ingest(filePath: String, platform: String, provider: String = "ollama") async throws -> [String: String] {
        let body = try? JSONSerialization.data(withJSONObject: ["file_path": filePath, "platform": platform, "provider": provider])
        return try await request(path: "/ingest", method: "POST", body: body)
    }
    func fetchIngestStatus() async throws -> IngestStatus {
        return try await request(path: "/ingest/status")
    }
}

// --- Response Models ---

struct IngestStatus: Codable {
    let running: Bool
    let total: Int
    let processed: Int
    let currentTitle: String
    let error: String?

    var progress: Double {
        guard total > 0 else { return 0 }
        return Double(processed) / Double(total)
    }

    enum CodingKeys: String, CodingKey {
        case running, total, processed, error
        case currentTitle = "current_title"
    }
}

struct AskResponse: Codable {
    let answer: String
    let hitType: String
    let referencedSessions: [Session]
    let tokensUsed: Int
    enum CodingKeys: String, CodingKey {
        case answer, hitType = "hit_type", referencedSessions = "referenced_sessions", tokensUsed = "tokens_used"
    }
}
