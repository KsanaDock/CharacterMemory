# 【技术杂谈】游戏 AI 记忆系统进化论：从 Memori 到 CharacterMemory 的低成本实践

大家好，我是 KsanaDock。

最近在研究游戏内 AI 角色的记忆系统，发现了一个非常强大的开源项目：**Memori**。它号称是“企业级 AI 记忆编织层”，功能非常全面。但经过一番深入研究，我发现它虽然强大，但对于我们这种追求**极致低延迟**和**低 Token 成本**的游戏场景来说，可能有点“杀鸡用牛刀”了。

于是，我基于 Memori 的思路，结合游戏开发的实际痛点，搞了一个“折中”方案——**CharacterMemory**。今天就来和大家聊聊这两个项目，以及我在做 CharacterMemory 时的思考和未来规划。

---

## 1. Memori：全能的记忆引擎

[Memori (GitHub)](https://github.com/MemoriLabs/Memori) 是一个非常成熟的通用记忆层解决方案。

### 核心亮点：
*   **全平台兼容**：支持 OpenAI, Anthropic 等主流 LLM，也支持 LangChain 等框架。
*   **存储无关性**：底层支持 Postgres, SQLite, MongoDB 等多种数据库。
*   **高级增强 (Advanced Augmentation)**：它不仅仅是存储对话，还会自动在后台分析实体 (Entity)、关系 (Relationship)、事实 (Facts) 等，构建一个知识图谱。
*   **自动归因**：能自动区分是谁 (Entity) 在什么场景 (Process) 下产生的记忆。

### 痛点分析：
虽然 Memori 很强，但如果你想把它直接塞进一个每秒需要处理几十个 NPC 交互的游戏里，问题就来了：
1.  **延迟 (Latency)**：Memori 的很多“增强”功能依赖于实时的 LLM 分析。如果每一句话都要经过 LLM 提炼三元组、更新图谱，那个延迟（几秒甚至更久）在回合制游戏里可能还凑合，但在实时交互中就是灾难。
2.  **成本 (Cost)**：全量分析意味着海量的 Token 消耗。对于独立开发者或小型游戏项目，这个 API 账单可能会让你破产。

---

## 2. CharacterMemory：为游戏而生的“折中”方案

既然纯 LLM 分析太贵太慢，纯向量检索又不够精准，我就搞了这个 **CharacterMemory**。

[GitHub: CharacterMemory](https://github.com/KsanaDock/CharacterMemory)

### 核心设计哲学：Lazy & Thrifty (懒惰且节俭)

我们不做全量的实时分析，而是采用**按需处理**的策略。

#### 🚀 核心机制：基于切片的动态总结 (Dynamic Summary based on Slice)

并不是所有的对话都需要 LLM 去深思熟虑。
*   **短对话 (Short Context)**：如果玩家只是说了一句“你好”或者“吃了吗”，我们直接存入向量库。因为这些短文本本身的语义就很清晰，直接向量化检索效果就很好，不需要浪费 LLM Token 去总结。
*   **长对话 (Long Context)**：只有当单次交互文本超过一定阈值（比如 100 字符），系统判定这包含了复杂的信息量时，才会触发 LLM 的 **Summarization (总结)** 功能。
    *   **浓缩**：LLM 会把这段长文浓缩成一句精炼的 Summary。
    *   **索引**：我们将这个 Summary 存入向量库用于检索，而将原始长文作为 Metadata 存储。
    *   **检索**：当检索时，我们匹配的是高密度的 Summary，命中率更高，干扰更少。

**效果**：
*   **降低延迟**：90% 的日常短对话直接绕过 LLM 总结步骤，毫秒级入库。
*   **节省成本**：只把 Token 用在刀刃（长文本）上。

### 目前已实现功能：
*   ✅ **混合存储**：JSON (Profile) + ChromaDB (Memory Stream)。
*   ✅ **切片总结**：自动判断文本长度，超长自动浓缩。
*   ✅ **每日反思**：仅在游戏内“一天”结束时进行一次全量的 LLM 反思 (Reflection)，更新性格和关系，极大降低高频交互成本。
*   ✅ **Streamlit 演示**：提供了一个可视化的 Debug 界面。

---

## 3. 未来规划 (Roadmap)

为了贯彻“低成本、低延时”的目标，后续的开发将围绕**量化**和**优化**展开：

### 📊 成本监控系统 (Cost & Metrics)
既然主打低成本，就不能光凭感觉。
*   **Token 计数器**：实时计算每次交互消耗的 Input/Output Token。
*   **金钱估算**：接入主流模型（如 GPT-4o-mini, DeepSeek）的计费标准，直接显示“这一聊花了多少钱”。
*   **内存/耗时监控**：监控向量检索耗时和内存占用，确保在低配服务器甚至本地端侧也能跑。

### 🧠 记忆遗忘与压缩 (Forgetting & Compression)
游戏玩久了，存档会越来越大。
*   **记忆衰减**：根据时间戳和重要性 (Importance)，自动清理低价值的记忆。
*   **分级存储**：短期记忆在内存，长期记忆落盘，死记忆归档。

### 🎮 游戏引擎集成
*   **Unity/Unreal SDK**：封装成 HTTP API 或本地 DLL，让游戏客户端能直接调用。

---

## 结语

Memori 是通用的“大脑”，而 CharacterMemory 是专为游戏角色定制的“反射弧”。我们不追求面面俱到，只追求在有限的算力下，让 NPC 活得更像人。

欢迎大家 Star 🌟 和 PR，一起探索低成本 AI 游戏的无限可能！

👉 [GitHub: CharacterMemory](https://github.com/KsanaDock/CharacterMemory)
