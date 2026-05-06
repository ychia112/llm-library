import SwiftUI
import UniformTypeIdentifiers

struct LibraryView: View {
    @State private var viewModel = LibraryViewModel()
    @Binding var selectedSessionID: String?
    
    let platforms = ["All", "ChatGPT", "Claude"]
    let questionTypes = ["All", "Debug", "HowTo", "Design", "Research"]
    
    // Extracted to reduce complexity in body
    private var isShowingTopicOverview: Bool {
        viewModel.selectedTopic == nil
        && viewModel.selectedTags.isEmpty
        && viewModel.selectedPlatform == "All"
        && viewModel.selectedQuestionType == "All"
    }
    
    var body: some View {
        HSplitView {
            leftFilters
            rightContent
        }
        .navigationTitle("Library")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                importMenu
            }
        }
        .task {
            await viewModel.loadOverview()
        }
        .onChange(of: viewModel.selectedPlatform) { _, _ in Task { await viewModel.loadSessions() } }
        .onChange(of: viewModel.selectedQuestionType) { _, _ in Task { await viewModel.loadSessions() } }
        .onChange(of: viewModel.selectedTopic) { _, _ in Task { await viewModel.loadSessions() } }
        .onChange(of: viewModel.selectedTags) { _, _ in Task { await viewModel.loadSessions() } }
        .alert("Import Status", isPresented: $viewModel.showInfoAlert) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(viewModel.alertMessage ?? "Unknown status")
        }
    }
    
    // MARK: - Subviews split to simplify type-checking
    
    private var leftFilters: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                filterSection(title: "Platform", items: platforms, selection: $viewModel.selectedPlatform)
                filterSection(title: "Type", items: questionTypes, selection: $viewModel.selectedQuestionType)
                
                VStack(alignment: .leading, spacing: 8) {
                    Text("Popular Tags")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundStyle(.secondary)
                    
                    FlowLayout(spacing: 6) {
                        ForEach(viewModel.topTags) { tagStat in
                            Toggle(tagStat.tag, isOn: Binding(
                                get: { viewModel.selectedTags.contains(tagStat.tag) },
                                set: { _ in viewModel.toggleTag(tagStat.tag) }
                            ))
                            .toggleStyle(.button)
                            .controlSize(.small)
                            .buttonStyle(.bordered)
                        }
                    }
                }
            }
            .padding()
        }
        .frame(minWidth: 150, maxWidth: 200)
    }
    
    @ViewBuilder
    private var rightContent: some View {
        VStack(spacing: 0) {
            if let overview = viewModel.overview {
                kpiStrip(overview: overview)
                    .background(.thinMaterial)
            }
            
            if isShowingTopicOverview {
                topicsGrid
            } else {
                filteredSessionsList
            }
        }
    }
    
    @ViewBuilder
    private func kpiStrip(overview: LibraryOverview) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 16) {
                kpiCard(title: "Total Sessions", value: "\(overview.totalSessions)", icon: "message.fill")
                if let topTopic = overview.byTopic.max(by: { $0.count < $1.count }) {
                    kpiCard(title: "Top Topic", value: topTopic.topic, icon: "tag.fill")
                }
                if let topTag = overview.topTags.first {
                    kpiCard(title: "Most Used Tag", value: "#\(topTag.tag)", icon: "number")
                }
            }
            .padding()
        }
    }
    
    private var topicsGrid: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 240))], spacing: 16) {
                ForEach(viewModel.topics) { topic in
                    TopicCardView(topic: topic, isSelected: false)
                        .onTapGesture {
                            viewModel.selectedTopic = topic.topic
                        }
                }
            }
            .padding()
        }
    }
    
    private var filteredSessionsList: some View {
        VStack(alignment: .leading) {
            filteredHeader
                .padding([.horizontal, .top])
            
            List(viewModel.sessions, selection: $selectedSessionID) { session in
                sessionRow(session)
                    .padding(.vertical, 4)
                    .tag(session.id)
            }
            .listStyle(.inset)
        }
    }
    
    @ViewBuilder
    private var filteredHeader: some View {
        HStack {
            if let topic = viewModel.selectedTopic {
                Text(topic)
                    .font(.title2)
                    .fontWeight(.bold)
                Button {
                    viewModel.selectedTopic = nil
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            } else {
                Text("Filtered Sessions")
                    .font(.title2)
                    .fontWeight(.bold)
            }
            Spacer()
        }
    }
    
    private func sessionRow(_ session: Session) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(session.title)
                .font(.headline)
            Text(session.summary ?? "No summary")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
    }
    
    private var importMenu: some View {
        Menu {
            Button("Import ChatGPT JSON") { selectFile(platform: "chatgpt") }
            Button("Import Claude JSON") { selectFile(platform: "claude") }
        } label: {
            Label("Import", systemImage: "plus.square.and.arrow.down")
        }
    }
    
    private func filterSection(title: String, items: [String], selection: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .fontWeight(.bold)
                .foregroundStyle(.secondary)
            
            Picker("", selection: selection) {
                ForEach(items, id: \.self) { item in
                    Text(item).tag(item)
                }
            }
            .labelsHidden()
        }
    }
    
    private func kpiCard(title: String, value: String, icon: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.accentColor)
            VStack(alignment: .leading) {
                Text(title)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(value)
                    .font(.headline)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color(nsColor: .controlBackgroundColor)))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.secondary.opacity(0.1), lineWidth: 1))
    }

    private func selectFile(platform: String) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.json]
        
        if panel.runModal() == .OK {
            if let url = panel.url {
                Task {
                    await viewModel.importFile(path: url.path, platform: platform)
                }
            }
        }
    }
}

// 簡易 FlowLayout 用於顯示標籤
struct FlowLayout: Layout {
    var spacing: CGFloat
    
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var currentX: CGFloat = 0
        var currentY: CGFloat = 0
        var lineHeight: CGFloat = 0
        
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX + size.width > width {
                currentX = 0
                currentY += lineHeight + spacing
                lineHeight = 0
            }
            currentX += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
        return CGSize(width: width, height: currentY + lineHeight)
    }
    
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var currentX = bounds.minX
        var currentY = bounds.minY
        var lineHeight: CGFloat = 0
        
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX + size.width > bounds.maxX {
                currentX = bounds.minX
                currentY += lineHeight + spacing
                lineHeight = 0
            }
            subview.place(at: CGPoint(x: currentX, y: currentY), proposal: .unspecified)
            currentX += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
    }
}
