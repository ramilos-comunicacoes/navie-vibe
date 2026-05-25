# Naviê Vibe - B2B AI Tasks Integration Specification

This document provides the complete API schema, database representation, and natural language prompt templates to integrate an autonomous AI agent into the Naviê B2B lodging system.

---

## 1. Database Model Representation

The `Tarefa` model acts as the core B2B operational unit. An AI agent should understand and map to these fields when reading or writing tasks:

| Field Name | Type | Choices / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key (auto-increment) | Unique task identifier |
| `hotel` | ForeignKey | References `Hotel` | Establishments ownership constraint |
| `titulo` | String | Max 255 chars | Clear operational title |
| `descricao` | Text | Optional | Instructions, descriptions, or observations |
| `prioridade` | String | `'baixa'`, `'normal'`, `'alta'` | Task execution urgency level |
| `status` | String | `'todo'`, `'doing'`, `'done'` | Current kanban execution state |
| `data_vencimento`| Date | Format: `YYYY-MM-DD` | Target deadline for the staff |
| `responsavel` | ForeignKey | References `ParceiroUsuario` | Assigned staff member profile |
| `unidade` | ForeignKey | References `UnidadeQuarto` | Linked room/chalet unit |
| `reserva` | ForeignKey | References `Reserva` | Associated guest booking |

---

## 2. API Schema for B2B Controllers

The following Django views are exposed as functional endpoints. An AI agent or a functional toolchain (JSON-RPC / Function Calling) can target them with raw HTTP requests.

### 2.1. Create Task
* **Endpoint:** `{% url 'hoteis:partner_criar_tarefa' %}` (mapped to `/hospedagens/atividades/criar/`)
* **Method:** `POST`
* **Request Payload (Form Data):**
  - `titulo` (string, required): Title of the task.
  - `descricao` (string, optional): Detailed text instructions.
  - `prioridade` (string, choices: `'baixa'`, `'normal'`, `'alta'`): Default is `'normal'`.
  - `status` (string, choices: `'todo'`, `'doing'`, `'done'`): Default is `'todo'`.
  - `data_vencimento` (string, format `YYYY-MM-DD`): Deadline.
  - `responsavel_id` (integer, optional): Primary key of the staff member.
  - `unidade_id` (integer, optional): Primary key of the room unit.
  - `reserva_id` (integer, optional): Primary key of the booking.
* **Headers:** Send `HX-Request: true` to receive a lightweight `HX-Redirect` response instead of a full HTML reload.

### 2.2. Edit Task
* **Endpoint:** `{% url 'hoteis:partner_editar_tarefa' tarefa_id=task_id %}` (mapped to `/hospedagens/atividades/editar/<int:tarefa_id>/`)
* **Method:** `POST`
* **Request Payload:** Same parameters as Create Task. Modifies the existing record in-place.

### 2.3. Delete Task
* **Endpoint:** `{% url 'hoteis:partner_deletar_tarefa' tarefa_id=task_id %}` (mapped to `/hospedagens/atividades/deletar/<int:tarefa_id>/`)
* **Method:** `POST` (requires `@require_POST`)

### 2.4. Update Task Status (Drag & Drop)
* **Endpoint:** `{% url 'hoteis:partner_mudar_status_tarefa' tarefa_id=task_id %}` (mapped to `/hospedagens/atividades/mudar-status/<int:tarefa_id>/`)
* **Method:** `POST`
* **Payload:**
  - `status` (string, choices: `'todo'`, `'doing'`, `'done'`, `'overdue'`).

---

## 3. Conversational AI Tool calling (NLP Interface)

The Assistente AI floating B2B chat view `/hospedagens/ia_chat/` (`ia_enviar_chat`) acts as a smart NLP router. It supports conversational command parsing. When implementing a real autonomous LLM agent, mount the following system prompt instructions:

### System Prompt for REAL LLM Agent Integration
```text
You are the Naviê AI B2B Assistant for [Hotel Name].
You have access to the following operational tools to manage tasks, staff, and room units:

1. list_tasks(filters: dict) -> list
2. create_task(title: str, due_date: str, priority: str, responsavel_id: int, room_id: int) -> dict
3. update_task_status(task_id: int, target_status: str) -> dict

Guidelines:
- If the user asks for their tasks or what to do, parse if they mean "today" or "high priority" and invoke list_tasks with appropriate filters.
- If the user asks to schedule, arrange, or plan a task (e.g. "atribua uma faxina no quarto 101 para maria amanhã"), extract:
  - title: e.g. "Faxina e Higienização"
  - due_date: parse relative words like "amanhã" into YYYY-MM-DD
  - responsavel_id: match employee name against the team members list
  - room_id: match room identifier (e.g., "101") against active units list
  - Invoke create_task.
- If the user asks to mark a task as in-progress or done (e.g. "marque a tarefa 5 como fazendo"), invoke update_task_status with the target status.
- Return response in polite, professional Portuguese. Include a friendly tip suggesting a page refresh to update the kanban board.
```

---

## 4. Live Simulated NLP Capabilities (Ready for Demo)

The system currently runs an advanced, regex-driven mock LLM processor directly inside `views.py:ia_enviar_chat`. It is fully capable of:
1. **Querying Database:** Listing tasks by priority, date, or status.
2. **Mutating Database:** Modifying status by parsing Task ID.
3. **Inserting Database:** Dynamic parsing of date shifts ("amanhã"), staff name matching, and unit number matching (e.g. "Suíte 101") to seamlessly populate task objects.
