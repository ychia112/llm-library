import SwiftUI
import UniformTypeIdentifiers

struct LibraryView: View {
    @State private var viewModel = LibraryViewModel()
    @Binding var selectedSessionID: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 32) {
                headerSection
                    .padding(.top, 8)

                if viewModel.isLoading && viewModel.topics.isEmpty {
                    ProgressView()
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.top, 60)
                } else if viewModel.topics.isEmpty && !viewModel.isImporting {
                    emptyState
                } else {
                    topicsGrid
                }
            }
            .padding(.horizontal, 28)
            .padding(.bottom, 28)
        }
        .safeAreaInset(edge: .top) {
            if let status = viewModel.ingestStatus {
                ingestBanner(status)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.3, dampingFraction: 0.85), value: viewModel.ingestStatus != nil)
        .background(Color(nsColor: .windowBackgroundColor))
        .navigationTitle("")
        .navigationDestination(for: TopicSummary.self) { topic in
            TopicDetailView(topic: topic, selectedSessionID: $selectedSessionID)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) { importMenu }
        }
        .task { await viewModel.loadOverview() }
        .alert("Import Status", isPresented: $viewModel.showInfoAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.alertMessage ?? "")
        }
    }

    // MARK: - Header

    private var headerSection: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 5) {
                Text("Knowledge Library")
                    .font(.system(size: 26, weight: .bold, design: .rounded))

                Group {
                    if let overview = viewModel.overview {
                        Text("\(overview.totalSessions) sessions · \(viewModel.topics.count) topics")
                    } else if viewModel.isLoading {
                        Text("Loading…")
                    } else {
                        Text("No conversations yet")
                    }
                }
                .font(.subheadline)
                .foregroundStyle(.secondary)
            }

            Spacer()
            connectionDot
        }
    }

    private var connectionDot: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(APIClient.shared.isConnected ? Color.green : Color.red)
                .frame(width: 6, height: 6)
            Text(APIClient.shared.isConnected ? "Connected" : "Offline")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
    }

    // MARK: - Ingest progress banner

    private func ingestBanner(_ status: IngestStatus) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                ProgressView()
                    .controlSize(.small)
                    .tint(.accentColor)

                VStack(alignment: .leading, spacing: 2) {
                    if status.total > 0 {
                        Text("Tagging conversation \(status.processed) of \(status.total)")
                            .font(.system(size: 12, weight: .medium))
                    } else {
                        Text("Parsing conversations…")
                            .font(.system(size: 12, weight: .medium))
                    }
                    if !status.currentTitle.isEmpty {
                        Text(status.currentTitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }

                Spacer()

                if status.total > 0 {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("\(Int(status.progress * 100))%")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(.secondary)
                        Text("\(status.processed)/\(status.total)")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                }
            }
            .padding(.horizontal, 28)
            .padding(.vertical, 10)

            if status.total > 0 {
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Rectangle().fill(.secondary.opacity(0.1))
                        Rectangle()
                            .fill(Color.accentColor.opacity(0.6))
                            .frame(width: geo.size.width * status.progress)
                            .animation(.linear(duration: 0.4), value: status.progress)
                    }
                }
                .frame(height: 2)
            }
        }
        .background(.ultraThinMaterial)
    }

    // MARK: - Grid

    private var topicsGrid: some View {
        LazyVGrid(
            columns: [GridItem(.adaptive(minimum: 240, maximum: 360))],
            spacing: 14
        ) {
            ForEach(viewModel.topics) { topic in
                NavigationLink(value: topic) {
                    TopicCardView(topic: topic)
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Empty state

    private var emptyState: some View {
        VStack(spacing: 14) {
            Image(systemName: "books.vertical")
                .font(.system(size: 44))
                .foregroundStyle(.quaternary)

            Text("Your library is empty")
                .font(.title3)
                .fontWeight(.medium)
                .foregroundStyle(.secondary)

            Text("Import conversations to get started.")
                .font(.subheadline)
                .foregroundStyle(.tertiary)

            Menu {
                Button("Import ChatGPT Export") { selectFile(platform: "chatgpt") }
                Button("Import Claude Export") { selectFile(platform: "claude") }
            } label: {
                Label("Import Conversations", systemImage: "square.and.arrow.down")
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            .menuStyle(.borderlessButton)
            .fixedSize()
            .padding(.top, 4)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 60)
    }

    // MARK: - Toolbar

    private var importMenu: some View {
        Menu {
            Button("Import ChatGPT Export") { selectFile(platform: "chatgpt") }
            Button("Import Claude Export") { selectFile(platform: "claude") }
        } label: {
            Label("Import", systemImage: "square.and.arrow.down")
        }
    }

    private func selectFile(platform: String) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.json]
        if panel.runModal() == .OK, let url = panel.url {
            Task { await viewModel.importFile(path: url.path, platform: platform) }
        }
    }
}

// MARK: - FlowLayout (shared with TopicDetailView)

struct FlowLayout: Layout {
    var spacing: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0
        var y: CGFloat = 0
        var lineH: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > width { x = 0; y += lineH + spacing; lineH = 0 }
            x += size.width + spacing
            lineH = max(lineH, size.height)
        }
        return CGSize(width: width, height: y + lineH)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var lineH: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX { x = bounds.minX; y += lineH + spacing; lineH = 0 }
            subview.place(at: CGPoint(x: x, y: y), proposal: .unspecified)
            x += size.width + spacing
            lineH = max(lineH, size.height)
        }
    }
}
