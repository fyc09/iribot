
# Data Structure Flowchart

## Core Data Structures

```mermaid
erDiagram
    Session ||--o{ Record : contains
    Session {
        string id
        string title
        datetime created_at
        datetime updated_at
    }

    Record ||--|| MessageRecord : "type=message"
    Record ||--|| ToolCallRecord : "type=tool_call"

    MessageRecord {
        string type "='message'"
        string role "system|user|assistant"
        string content
        list binary_content
        datetime timestamp
    }

    ToolCallRecord {
        string type "='tool_call'"
        string tool_call_id
        string tool_name
        dict arguments
        any result
        boolean success
        datetime timestamp
    }
```

## Message Flow Transformation Process

```mermaid
flowchart TB
    subgraph User["User Input"]
        U1["ChatRequest - session_id - message - binary_content"]
    end

    subgraph Storage["Session Records Storage Format"]
        R1["MessageRecord {type: 'message', role, content}"]
        R2["ToolCallRecord {type: 'tool_call', tool_call_id, tool_name, arguments, result, success}"]
    end

    subgraph Transform["get_messages_for_llm() Transformation"]
        T1["1. Count total tool calls"]
        T2["2. Calculate truncation_threshold = total - tool_history_rounds"]
        T3["3. Iterate records, build messages"]
        T4["4. Truncate old tool calls by threshold"]
    end

    subgraph LLM["OpenAI API Message Format"]
        L1["{role: 'system', content}"]
        L2["{role: 'user', content}"]
        L3["{role: 'assistant', content, tool_calls: [...]}"]
        L4["{role: 'tool', tool_call_id, content: result}"]
    end

    U1 --> R1
    U1 --> R2
    R1 --> T1
    R2 --> T1
    T1 --> T2
    T2 --> T3
    T3 --> T4
    T4 --> L1
    T4 --> L2
    T4 --> L3
    T4 --> L4
```

## Tool Call Loop Process

```mermaid
flowchart TD
    START(["Start Tool Call Loop"]) --> LoopCheck{"iteration < max_iterations"}

    LoopCheck -->|No| MaxReached["Save reached_max_iterations message"]
    MaxReached --> END(["End"])

    LoopCheck -->|Yes| GetMsg["get_messages_for_llm()"]
    GetMsg --> Chat["agent.chat_stream() calls OpenAI API"]

    Chat --> Parse{"Parse response"}
    Parse --> HasTool{"Has tool_calls?"}

    HasTool -->|No| NoTool["Save assistant message"]
    NoTool --> Done{{"Send 'done' event"}}
    Done --> END

    HasTool -->|Yes| HasThinking{"Has thinking content?"}

    HasThinking -->|Yes| SaveThinking["Save thinking MessageRecord, send 'record' event"]
    HasThinking -->|No| SkipThinking

    SaveThinking --> AddCtx["Add assistant message to context with tool_calls"]
    SkipThinking --> AddCtx

    AddCtx --> Signal["Send 'tool_calls_start' event"]
    Signal --> ExecLoop{"Iterate tool_calls"}

    ExecLoop --> Execute["Execute tool call agent.process_tool_call()"]
    Execute --> SaveRecord["Save ToolCallRecord, send 'tool_result' event"]
    SaveRecord --> AddResult["Add tool result to context"]
    AddResult --> MoreTool{"More tool_calls?"}

    MoreTool -->|Yes| ExecLoop
    MoreTool -->|No| LoopCheck
```

## Tool Call Truncation Logic

Assume `tool_history_rounds = 3`:

```mermaid
flowchart LR
    subgraph History["History"]
        Rec1["Msg1"]
        Tc1["Tool1"]
        Res1["Result1"]
        Rec2["Msg2"]
        Tc2["Tool2"]
        Res2["Result2"]
        Rec3["Msg3"]
        Tc3["Tool3"]
        Res3["Result3"]
    end

    subgraph Truncated["Truncated as seen by LLM"]
        Rec1t["Msg1"]
        Tc1t["Tool1 (name only)"]
        Rec2t["Msg2"]
        Tc2t["Tool2 (full)"]
        Res2t["Result2"]
        Rec3t["Msg3"]
        Tc3t["Tool3 (full)"]
        Res3t["Result3"]
    end

    Rec1 --> Rec1t
    Tc1 -->|"Truncate"| Tc1t
    Tc2 -->|"Keep full"| Tc2t
    Res2 --> Res2t
    Tc3 -->|"Keep full"| Tc3t
    Res3 --> Res3t
```

## Configuration Parameters

```mermaid
classDiagram
    class settings {
        <<Global Config>>
        openai_api_key: str
        openai_base_url: str | None
        openai_model: str = "gpt-4o"
        tool_history_rounds: int = 10
        +get(key) value
    }
```

## Data Flow Overview

```mermaid
flowchart TB
    subgraph API["FastAPI Endpoints"]
        API1["POST /chat receives ChatRequest"]
        API2["GET /sessions list sessions"]
        API3["POST /sessions create session"]
    end

    subgraph SM["SessionManager"]
        SM1["Memory cache: sessions dict"]
        SM2["File storage: ./sessions/{id}.json"]
    end

    subgraph Transform2["Message Transformation"]
        T21["Message construction"]
        T22["Tool truncation"]
    end

    subgraph LLM["LLM Interaction"]
        LLM1["chat_stream()"]
        LLM2["process_tool_call()"]
    end

    API1 --> SM1
    API2 --> SM1
    API3 --> SM1
    SM1 --> SM2

    SM1 --> T21
    T21 --> T22
    T22 --> LLM1

    LLM1 -->|"tool_calls"| LLM2
    LLM2 -->|"result"| SM1
```
