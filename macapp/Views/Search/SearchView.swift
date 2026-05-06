import SwiftUI

struct SearchView: View {
    @State private var viewModel = SearchViewModel()
    @Binding var selectedSessionID: String?
    
    var body: some View {
        VStack(spacing: 0) {
            // 頂部搜尋框
            VStack {
                TextField("Search your conversation history...", text: $viewModel.query)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        Task { await viewModel.performSearch() }
                    }
                    .padding()
            }
            .background(.thinMaterial)
            
            // 結果清單
            ZStack {
                if viewModel.isLoading {
                    ProgressView("Searching...")
                } else if let error = viewModel.errorMessage {
                    ContentUnavailableView("Search Failed", systemImage: "exclamationmark.triangle", description: Text(error))
                } else if viewModel.results.isEmpty && !viewModel.query.isEmpty {
                    ContentUnavailableView("No Results", systemImage: "magnifyingglass", description: Text("Try different keywords."))
                } else {
                    List(selection: $selectedSessionID) {
                        ForEach(viewModel.results) { result in
                            SearchResultCard(result: result)
                                .tag(result.session.id)
                        }
                    }
                    .listStyle(.inset)
                }
            }
            
            // 底部狀態列
            if !viewModel.hitType.isEmpty {
                HStack {
                    statusIcon
                    Text(statusText)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Spacer()
                }
                .padding()
                .background(statusColor.opacity(0.1))
                .foregroundStyle(statusColor)
            }
        }
        .navigationTitle("Search")
    }
    
    // 狀態列輔助計算
    private var statusColor: Color {
        switch viewModel.hitType.lowercased() {
        case "hit": return .green
        case "partial": return .orange
        case "miss": return .red
        default: return .secondary
        }
    }
    
    private var statusIcon: some View {
        switch viewModel.hitType.lowercased() {
        case "hit": return Image(systemName: "checkmark.circle.fill")
        case "partial": return Image(systemName: "bolt.fill")
        case "miss": return Image(systemName: "xmark.circle.fill")
        default: return Image(systemName: "info.circle")
        }
    }
    
    private var statusText: String {
        switch viewModel.hitType.lowercased() {
        case "hit": return "✓ Found in library — 0 tokens used"
        case "partial": return "⚡ Partial match — context injected"
        case "miss": return "✗ Not in library — LLM was queried"
        default: return ""
        }
    }
}

struct SearchResultCard: View {
    let result: SearchResult
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                // Similarity 圓環百分比
                Text("\(Int(result.similarity * 100))%")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .monospacedDigit()
                    .padding(4)
                    .background(Circle().fill(.secondary.opacity(0.2)))
                
                Text(result.session.title)
                    .font(.headline)
                    .lineLimit(1)
                
                Spacer()
                
                Text(result.session.platform.uppercased())
                    .font(.caption2)
                    .fontWeight(.bold)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(.secondary.opacity(0.15)))
            }
            
            if let summary = result.session.summary {
                Text(summary)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            
            // Tags Pills
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    ForEach(result.session.tags.prefix(5), id: \.self) { tag in
                        Text(tag)
                            .font(.caption2)
                            .monospaced()
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Capsule().stroke(.secondary.opacity(0.5), lineWidth: 1))
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }
}
