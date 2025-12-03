# AI Character Memory System

A locally deployable AI character memory system that supports long-term memory, structured profile management, and agentic reflection.

[English](README_EN.md) | [中文](README.md)

## 📖 Introduction

This project is designed to serve as a memory system for AI characters in games. It specifically addresses the challenge of vectorizing memory data by avoiding the "slicing problem" (context fragmentation) while preserving the semantic understanding capabilities of vectorization.

## 📂 Project Structure

```
d:\MyProj\character-memory\
├── data/                  # 💾 Runtime Data Storage
│   ├── profile.json       # Character profile (Name, Personality, Daily Log, etc.)
│   └── chroma_db/         # Vector Database (ChromaDB) for semantic memory retrieval
├── src/                   # 🧠 Source Code
│   ├── app.py             # Main Streamlit Application (Frontend & Entry Point)
│   ├── core/              # Core Logic
│   │   └── memory_manager.py # Manages profile, retrieval, and reflection logic
│   ├── models/            # Data Schemas
│   │   └── schema.py      # Pydantic models (CharacterProfile, MemoryItem, DailyLogEntry)
│   ├── services/          # External Services
│   │   └── llm_service.py # LLM Integration (OpenRouter/OpenAI)
│   └── storage/           # Data Access Layer
│       ├── json_store.py  # Handles profile.json operations
│       └── vector_store.py# Handles ChromaDB operations
├── docs/                  # Documentation
└── requirements.txt       # Python Dependencies
```

## 💾 Data Storage

-   **Profile Data**: Stored in `data/profile.json`. This file contains the character's structured state, including:
    -   Basic Info (Name, Occupation)
    -   Personality & Values
    -   Relationships
    -   **Daily Log** (Record of activities and interactions)
    -   Status (Health, Wealth)

-   **Memory Data**: Stored in `data/chroma_db`. This is a local vector database that stores:
    -   Conversation history (User inputs & AI responses)
    -   Observations and Thoughts
    -   Each memory is embedded for semantic search (RAG).

## 🚀 How to Run

```bash
streamlit run src/app.py
```

## ✨ Key Features

1.  **RAG Memory**: Retrieves relevant past memories based on the current conversation.
2.  **Agentic Reflection**:
    -   Click **"🛑 End Conversation & Reflect"** to trigger a self-reflection process.
    -   The AI analyzes the chat, updates its mood/relationships, and writes a **Daily Log** entry.
3.  **Real-time Timing**: Displays the execution time for Retrieval (RAG) and Generation (LLM) in the UI.
4.  **Advanced RAG (Parent-Child Indexing)**:
    -   **Threshold-based Summarization**:
        -   **Short (<300 chars)**: Stored directly to preserve detail and save costs.
        -   **Long (>300 chars)**: Automatically summarized by LLM. The **Summary** is indexed for search, but the **Original Content** is retrieved for context.
    -   **Daily Log Integration**: Daily logs are also vectorized (as `daily_log` type) to ensure long-term retrieval of past activities.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 📞 Contact

<div align="center">

![KsanaDock Card](docs/时空码头.png)

</div>

If you have any questions or suggestions, please contact us via:

- Submit an Issue: [GitHub Issues](https://github.com/KsanaDock/CharacterMemory/issues)
- Official Website: [KsanaDock](https://www.ksanadock.com)

## 🌐 Follow Us

<div align="center">

### Follow our latest updates on social media

<table>
<tr>
<td align="center" width="200">
<a href="https://www.xiaohongshu.com/user/profile/653c5f81000000000301f274">
<img src="https://img.shields.io/badge/Xiaohongshu-FF2442?style=for-the-badge&logo=xiaohongshu&logoColor=white" alt="Xiaohongshu"/>
<br/>
<strong>Xiaohongshu</strong>
<br/>
<sub>Creative Sharing & Exchange</sub>
</a>
</td>
<td align="center" width="200">
<a href="https://space.bilibili.com/336052319">
<img src="https://img.shields.io/badge/Bilibili-00A1D6?style=for-the-badge&logo=bilibili&logoColor=white" alt="Bilibili"/>
<br/>
<strong>Bilibili</strong>
<br/>
<sub>Chinese Video Content</sub>
</a>
</td>
<td align="center" width="200">
<a href="https://github.com/KsanaDock">
<img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
<br/>
<strong>GitHub</strong>
<br/>
<sub>Source Code & Updates</sub>
</a>
</td>
</tr>
<tr>
<td align="center" width="200">
<a href="https://x.com/KsanaDock">
<img src="https://img.shields.io/badge/X-000000?style=for-the-badge&logo=x&logoColor=white" alt="X"/>
<br/>
<strong>X (Twitter)</strong>
<br/>
<sub>Latest News & Discussions</sub>
</a>
</td>
<td align="center" width="200">
<a href="https://www.youtube.com/@KsanaDock">
<img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube"/>
<br/>
<strong>YouTube</strong>
<br/>
<sub>Demos & Tutorials</sub>
</a>
</td>
</tr>
</table>

</div>

---

**Note**: Using this project requires a valid AI service API key. Please ensure you comply with the terms and conditions of each AI service provider.
