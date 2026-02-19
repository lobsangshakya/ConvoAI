# CHANGES.md

## [1.0.0] - 2026-02-15

### Added
- **Retrieval Augmented Generation (RAG)**: Backend now retrieves context from `/knowledge` folder before answering.
- **Streaming Support**: Real-time response streaming from AI to UI.
- **New Chat**: Ability to reset the conversation.
- **Health Endpoint**: `/health` to check API and RAG status.
- **Knowledge Base**: Sample `about_convoai.md` for testing.

### Improved
- **Modern UI**: Completely overhauled `App.css` with a premium dark theme and Inter typography.
- **Robust AI Client**: Standardized OpenAI client with improved timeouts and error handling.
- **Mobile Support**: Improved responsive layout for smaller screens.

### Fixed
- Replaced basic proxy logic with a professional RAG pipeline.
- Improved message bubble styling and visibility.
