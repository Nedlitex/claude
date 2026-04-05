# D:\edu — Backend Architecture Plan

## Context

The goal is to create a new Python project at `D:\edu` that replicates the backend architecture from `D:\daily_dose_of_ai` (with `D:\daily_dose_base` as the cleaner skeleton), focused on supporting an educational platform. The new project should have the same core layers — server, service manager, model management, AI model, env settings, scripts, building, unit testing — but refactored for better code quality: improved reuse, cleaner boundary separation, and more structured organization.

Key problems in the source to fix:
- `db_operations.py` is 4164+ lines of monolithic CRUD
- `_auto_register_services()` is ~500 lines of hardcoded factory registrations
- `BaseTask` is 700+ lines mixing 5 separate concerns
- Task inputs are inconsistent — some use plain dataclasses, some Pydantic BaseModel, some raw `__init__` args
- `env_vars/__init__.py` uses raw `os.environ.get()` with no validation
- Database engine created at import time, making testing painful

---

## Directory Structure

```
D:\edu\
├── pyproject.toml                    # Project metadata, deps, build config
├── pytest.ini                        # Pytest configuration
├── .pre-commit-config.yaml           # black, isort, autoflake, pyupgrade
├── .env.example                      # Environment variable template
├── .gitignore
├── scripts/
│   ├── README.md
│   └── check_imports.py              # Import boundary linter (pre-commit hook)
├── src/
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ��── context.py                        # AppContext container, init_context(), get_context()
│   ├── exceptions.py                     # Domain exception hierarchy
│   ├── config/
│   │   ├── __init__.py               # Re-exports get_config()
│   │   └── settings.py               # pydantic-settings AppConfig
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                   # Engine, SessionLocal, get_db_session, clone utils
│   │   ├── constants.py              # DatabaseEntryState, role constants
│   │   ├── models/
│   │   │   ├── __init__.py           # Re-exports all models + Base
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── task.py               # TaskModel, LogEntryModel
│   │   │   ├── file.py
│   │   │   ├── exam.py               # All exam-related ORM models
│   │   │   ├── service_config.py
│   │   │   └── activity.py           # ActivityModel (API usage, token tracking)
│   ├── dal/                              # Data Access Layer — SOLE DB boundary
│   │   ├── __init__.py               # DataAccessLayer facade class
│   │   ├── base.py                   # DALBase with session management
│   │   ├── user_dal.py               # User CRUD (returns schemas only)
│   │   ├── conversation_dal.py
│   │   ├── task_dal.py               # Task state, progress, heartbeat
│   │   ├── file_dal.py
│   │   ├── exam_dal.py               # All exam-related DB ops
│   │   ├── service_config_dal.py
│   │   └── activity_dal.py           # Activity records, usage aggregation
│   ├── schemas/                          # Domain schemas (Pydantic) — 1:1 with DB models
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseSchema (id, state, from_attributes=True)
│   │   ├── user.py                    # UserSchema, UserCreateSchema, UserUpdateSchema
│   │   ├── conversation.py
│   │   ├── task.py
│   │   ├── file.py
│   │   ├── exam.py
│   │   ├── service_config.py
│   │   └── activity.py               # ActivitySchema, UsageSummary, TokenUsage
│   ├── activity/                         # User activity tracking, token metering, throttling
│   │   ├── __init__.py               # get_activity(), set_activity(), clear_activity()
│   │   ├── context.py                # ActivityContext, ActivitySpan, SpanKind enum
│   │   ├── metering.py               # UsageSummary, TokenUsage
│   │   ├── throttle.py               # ThrottlePolicy, ThrottleManager
│   │   └── middleware.py             # FastAPI ActivityTrackingMiddleware
│   ├── i18n/
│   │   ��── __init__.py               # t(), set_locale(), get_locale(), load_locales()
│   │   └── locales/
│   │       ├── en.json               # English (default)
│   │       └── zh.json               # Chinese
│   ├── utilities/
│   │   ├── __init__.py               # Logger singleton
│   │   ├── logging.py                # Logger factory, handlers (console/file/DB)
│   │   ├── profile.py                # ExecutionProfile tracing
│   │   ├── time.py                   # Timezone-aware datetime
│   │   ├── retry.py                  # RetryPolicy, retry_async(), pre-built policies
│   │   └── clients/
│   │       ├── __init__.py
│   │       ├── s3_client.py
│   │       └── mock_s3_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_model.py             # AIModelBase, AIConversationBase, message types
│   │   ├── task_conversation.py      # TaskConversation — task-aware wrapper with progress/cancel/resume
│   │   ├��─ openai_model.py           # OpenAI implementation
│   │   ├── claude_model.py           # Claude implementation
│   │   └── mock_model.py            # MockAIModel — deterministic responses for testing
│   ├── tools/
│   │   ├── __init__.py
│   │   └── base_tool.py              # AIToolBase for function calling
│   ├── prompts/                          # Externalized prompt templates (Jinja2)
│   │   ├── __init__.py               # PromptLoader, render_prompt()
│   │   ├── shared/                   # Reusable prompt fragments
│   │   │   └── output_json.md
│   │   └── exam/                     # Exam-specific prompts
│   │       ├── extract_problems.md
│   │       └── analyze_answer.md
│   ├── agents/                           # Agent wrappers for AI calls
│   │   ├── __init__.py
│   │   ├── base_agent.py             # BaseAgent[ResultT] — prompt + model + parsing
│   │   └── exam/
│   │       ├── __init__.py
│   │       ├── extract_problems_agent.py
│   │       └── analyze_answer_agent.py
│   ├── model_management/
│   │   ├── __init__.py               # Scenario constants + ModelManager re-export
│   │   └── model_manager.py          # Singleton, scenario-based model selection
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registry.py               # @register_service decorator + ServiceRegistry
│   │   ├── service_names.py          # String constants for service names
│   │   ├── base_task.py              # BaseTaskConfig + BaseTask[ConfigT] (generic, uses mixins)
│   │   ├── base_service.py           # BaseService (task queue, threading, lifecycle)
│   │   ├── task_state.py              # TaskState, TaskResultStatus, TaskResult, AgentStatus (all enums)
│   │   ├── recovery.py               # TaskRecoveryManager — crash recovery on startup
│   │   ├── components/                # Composed into BaseTask (NOT mixins — owned objects)
│   │   │   ├── __init__.py
│   │   │   ├── lifecycle.py           # LifecycleManager — state machine, pause/resume/cancel/retry
│   │   │   ├── progress.py            # ProgressTracker — hierarchical progress reporting
│   │   │   ├── db_tracking.py         # DBTracker — persist state/context/heartbeat to DB
│   │   │   ├── profiling.py           # Profiler — execution tracing
│   │   │   └── subtask.py             # SubtaskManager — child tracking, weighted submission
│   │   └── impl/
│   │       ├── __init__.py            # Imports all services (triggers registration)
│   │       ├── file_validate_service.py
│   │       ├── parse_service.py
│   │       └── exam_ingest_service.py
│   ├── service_management/
│   │   ├── __init__.py
│   │   ├── service_manager.py         # ServiceManager (delegates to backends)
│   │   └── backends/
│   │       ├── __init__.py
│   │       ├── base.py               # ServiceBackend protocol
│   │       ├── local_backend.py      # In-process task execution
│   │       └── remote_backend.py     # HTTP-based remote task execution
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── base_server.py             # BaseAPIServer (CORS, lifespan, auth, files)
│   │   ├── edu_server.py             # EduServer extends BaseAPIServer
│   │   ├── dependencies.py           # FastAPI DI: get_db, get_current_user
│   │   ├── apis/
│   │   │   ├── __init__.py
│   │   │   ├── authentication.py
│   │   │   ├── file.py
│   │   │   └── tasks.py
│   │   └── contracts/                # HTTP request/response shapes (distinct from domain schemas)
│   │       ├── __init__.py
│   │       ├── authentication.py     # LoginRequest, LoginResponse, TokenResponse
│   │       └── file.py               # FileUploadRequest, FileUploadResponse
│   └── data/                          # SQLite database files (dev)
├── tests/
│   ├── conftest.py                    # Shared fixtures, mock setup, override_context
│   ├── factories.py                   # Test factories: make_agent_state, make_task_context, etc.
│   ├── test_architecture.py           # Import boundaries, no bare except, file size limits
│   ├── activity/
│   │   ├── __init__.py
│   │   ├── test_context.py            # Span creation, nesting, thread-safety
│   │   ├── test_throttle.py           # Rate limit, cache expiry, policy enforcement
│   │   └── test_middleware.py         # Activity creation, persistence, exclusion, 429
│   ├── agents/
│   │   ├── __init__.py
│   │   └── test_base_agent.py         # Agent lifecycle, caching, resume
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── apis/
│   │   │   ├── __init__.py
│   │   │   ├── test_authentication.py
│   │   │   ├── test_tasks.py          # Submit, status, cancel, pause, resume, retry
│   │   │   └── test_file.py           # Upload, validation, auth
│   │   └── test_base_server.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── test_settings.py           # Defaults, env override, nested delimiter, validation
│   ├── dal/
│   │   ├── __init__.py
│   │   ├── test_user_dal.py
│   │   ├── test_exam_dal.py
│   │   ├── test_task_dal.py
│   │   ├── test_conversation_dal.py
│   │   ├── test_file_dal.py
│   │   ├── test_service_config_dal.py
│   │   └── test_activity_dal.py
│   ├── i18n/
│   │   ├── __init__.py
│   │   └── test_i18n.py               # Locale fallback, interpolation, ContextVar isolation
│   ├── model_management/
│   │   ├── __init__.py
│   │   └── test_model_manager.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── test_prompt_loader.py      # Render, missing var, include, StrictUndefined
│   ├── services/
│   │   ├── __init__.py
│   │   ├── components/
│   │   │   ├── __init__.py
│   │   │   ├── test_lifecycle.py      # All transitions, invalid transitions, thread-safe
│   │   │   ├── test_progress.py       # Leaf, weighted children, parent aggregation
│   │   │   ├── test_db_tracker.py     # Persist, heartbeat, debounce
│   │   │   └── test_subtask.py        # Parent-child linking, weight assignment
│   │   ├── test_base_service.py
│   │   ├── test_base_task.py
│   │   ├── test_registry.py
│   │   ├── test_recovery.py           # Orphaned detection, staleness, max retries, cascade
│   │   └── test_concurrent.py         # N tasks, no deadlock, no state corruption
│   ├── tools/
│   │   ├── __init__.py
│   │   └── test_base_tool.py          # Registration, param validation, execution, error
│   ├── utilities/
│   │   ├── __init__.py
│   │   ├── test_retry.py              # Policies, backoff, sleep_func injection, max retries
│   │   ├── test_time.py               # Timezone-aware datetime helpers
│   │   └── test_profile.py            # Execution tracing
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test_mock_model.py         # Canned responses, call history, sequence behavior
│   │   └── test_task_conversation.py  # Progress, cancel, resume, message threading
│   └── service_management/
│       ├── __init__.py
│       ├── test_service_manager.py    # Backend selection, task routing, lifecycle
│       └── test_local_backend.py      # In-process execution, thread management
└── .tracking/
    └── plans/
```

---

## Key Refactorings

### 1. Configuration: `pydantic-settings` replaces raw `os.environ`

**Source**: `src/env_vars/__init__.py` — 60+ bare `os.environ.get()` calls at module level, no validation, no grouping.

**New** (`src/config/settings.py`):
```python
class DatabaseConfig(BaseModel):
    pg_host: str = ""
    pg_port: int = 5432
    pg_username: str = ""
    pg_password: str = ""
    pg_dbname: str = "edu"
    sqlite_file_directory: str = "src/data/"

class AuthConfig(BaseModel):
    secret_key: str  # REQUIRED — no default. Server won't start without this.
    algorithm: str = "HS256"
    expire_minutes: int = Field(default=7 * 24 * 60, description="Token expiry (default: 7 days)")

class AIConfig(BaseModel):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250514"

class MockConfig(BaseModel):
    use_mock_s3: bool = False
    use_mock_model: bool = False

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
    database: DatabaseConfig = DatabaseConfig()
    auth: AuthConfig = AuthConfig()
    ai: AIConfig = AIConfig()
    mock: MockConfig = MockConfig()
    app_url: str = "localhost"
    app_port: int = 8000

_config: AppConfig | None = None
def get_config() -> AppConfig: ...
```

### 2. (Removed — superseded by DAL in refactoring #15)

### 3. Service registration: `@register_service` decorator replaces hardcoded factories

**Source**: `ServiceManager._auto_register_services()` — ~500 lines of copy-paste factory functions.

**New** (`src/services/registry.py`):
```python
@dataclass
class ServiceRegistration:
    name: str
    factory: Callable[[], BaseService]
    dependencies: set[str] = field(default_factory=set)

_registry: dict[str, ServiceRegistration] = {}

def register_service(name: str, dependencies: set[str] | None = None):
    """Class decorator that registers a service."""
    def decorator(cls):
        _registry[name] = ServiceRegistration(name=name, factory=cls, dependencies=dependencies or set())
        return cls
    return decorator
```

Usage in service files:
```python
@register_service(name=SERVICE_EXAM_INGEST, dependencies={SERVICE_FILE_VALIDATE})
class ExamIngestService(BaseService): ...
```

`ServiceManager.__init__` reads from registry instead of hardcoding.

### 4. BaseTask decomposition: Composed components

**Source**: `BaseTask` in `base_service.py` — 700+ lines mixing lifecycle, DB tracking, profiling, model access, subtask submission.

**New**: Split into `base_task.py` + `components/` directory. Components are **owned objects** (composition), NOT mixins (no multiple inheritance):
```python
class BaseTask(Generic[ConfigT]):
    def __init__(self, config: ConfigT, service_name: str, ...):
        self.lifecycle = LifecycleManager(self)    # state machine, pause/resume/cancel
        self.progress = ProgressTracker(self)       # hierarchical progress reporting
        self.tracking = DBTracker(self)             # DB persistence, context, heartbeat
        self.profiler = Profiler(self)              # execution tracing
        self.subtasks = SubtaskManager(self)        # child task tracking
```

Each component is independently testable (~50-100 lines each). Developers access capabilities via explicit delegation: `self.progress.report(30, "...")` not `self.progress.report(30, "...")`.

### 5. Lazy database initialization

**Source**: Engine created at module import time via module-level code in `database.py`.

**New**: `init_db(config: DatabaseConfig)` factory function, called explicitly during server startup. Tests can initialize with SQLite without env var hacks.

### 6. Typed `BaseTaskConfig` for all task inputs

**Source problem**: Task inputs are inconsistent across the codebase:
- `CrawlTaskConfig` — plain dataclass with `@dataclass` missing (just class attrs)
- `FileValidateTaskConfig` — plain class with annotated attrs
- `ExamAnswerAnalysisTaskConfig(BaseModel)` — Pydantic model
- `CrawlTask.__init__` — takes raw `url: str` parameter directly
- Some tasks have no config at all, just ad-hoc `__init__` parameters

**New** (`src/services/base_task.py`):
```python
from pydantic import BaseModel

class BaseTaskConfig(BaseModel):
    """Base config for all tasks. Child tasks inherit and add custom fields."""
    user_id: int = -1
    priority: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

`BaseTask` is generic on the config type:
```python
ConfigT = TypeVar("ConfigT", bound=BaseTaskConfig)

class BaseTask(Generic[ConfigT]):
    """Task with composed components — no mixin inheritance."""
    def __init__(
        self,
        task_config: ConfigT,
        service_name: str,
        task_id: int | None = None,
        model_overrides: dict[str, str] | None = None,
    ):
        self.config = task_config       # Typed, validated config
        self.user_id = task_config.user_id
        self.priority = task_config.priority
        ...
```

Child tasks define their own config:
```python
class ExamIngestTaskConfig(BaseTaskConfig):
    """Config for exam ingestion."""
    exam_id: int
    user_file_id: int
    extract_images: bool = True

class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        # Access typed config fields directly
        exam_id = self.config.exam_id
        file_id = self.config.user_file_id
        ...
```

Benefits:
- **Validation**: Pydantic validates config at construction time (missing fields, wrong types caught immediately)
- **Consistency**: Every task uses the same pattern — no more mixed dataclass/BaseModel/raw args
- **Serialization**: Configs are JSON-serializable for DB persistence, logging, and debugging
- **Type safety**: `self.config.exam_id` is typed — IDE autocomplete and type checking work
- **Inheritance**: Common fields (user_id, priority) defined once in `BaseTaskConfig`

### 7. Strict DB model / Schema class separation with 1:1 mapping

**Source problem**: ORM models leak throughout the codebase:
- `db_operations.py` returns raw ORM models (`UserModel`, `ExamModel`, etc.)
- API endpoints sometimes work with ORM models directly, sometimes with schemas
- `convert.py` exists to bridge this gap, but it's a workaround for a missing boundary
- Services receive and pass ORM objects, coupling them to the DB session lifecycle

**New pattern**: Every ORM model gets a corresponding Pydantic schema. DB operations always convert to/from schemas at the boundary.

**Directory structure** — schemas live in `src/schemas/` (separate from backend API schemas):
```
src/schemas/
├── __init__.py
├── base.py           # BaseSchema with common fields (id, state, timestamps)
├── user.py           # UserSchema, UserCreateSchema, UserUpdateSchema
├── conversation.py   # ConversationSchema, ThreadSchema
├── task.py           # TaskSchema
├── file.py           # FileSchema
├── exam.py           # ExamSchema, ExamProblemSchema, AnswerSheetSchema, etc.
└── service_config.py # ServiceConfigSchema
```

**BaseSchema pattern**:
```python
class BaseSchema(BaseModel):
    """Base schema for all domain objects."""
    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode
    id: int
    state: int = DatabaseEntryState.OK

class UserSchema(BaseSchema):
    username: str
    is_active: bool = True
    role: str = "student"
    create_timestamp: datetime | None = None
    last_login_timestamp: datetime | None = None

class UserCreateSchema(BaseModel):
    """Schema for creating a user (no id, no state)."""
    username: str
    password: str
    role: str = "student"
```

**DB operations boundary** — operations accept and return schemas:
```python
# src/db/operations/user_ops.py
class UserOps(CRUDBase[UserModel]):
    def get_by_id(self, session, id, include_deleted=False) -> UserSchema | None:
        obj = super()._get_by_id_raw(session, id, include_deleted)
        return UserSchema.model_validate(obj) if obj else None

    def create(self, session, data: UserCreateSchema, commit=True) -> UserSchema:
        obj = UserModel(**data.model_dump())
        session.add(obj)
        if commit:
            session.commit()
            session.refresh(obj)
        return UserSchema.model_validate(obj)

    def get_by_username(self, session, username: str) -> UserSchema | None:
        obj = session.query(self.model).filter(self.model.username == username).first()
        return UserSchema.model_validate(obj) if obj else None
```

**Rules enforced**:
1. **ORM models** (`src/db/models/`) — only used inside `db/operations/` and Alembic migrations
2. **Schemas** (`src/schemas/`) — used everywhere else: services, backend APIs, task configs
3. **DB operations** — the boundary layer: accepts schemas in, returns schemas out
4. **No ORM object escapes** the `db/` package — all consumers work with validated Pydantic schemas
5. **Backend API schemas** (`src/backend/schemas/`) remain separate — these are request/response shapes for the HTTP API, which may differ from domain schemas (e.g., omitting password_hashed, adding pagination metadata)

**Naming convention**:
- `UserModel` — ORM model (DB layer only)
- `UserSchema` — domain schema (used in services, tasks, APIs)
- `UserCreateSchema` — creation input (no id)
- `UserUpdateSchema` — partial update input
- `UserResponse` — HTTP API response shape (in `backend/schemas/`)

### 8. Formal task lifecycle state machine with hierarchical pause/resume/cancel

**Source problem**: Task state management is ad-hoc:
- `completed`, `cancelled` are bare booleans — no formal state enum
- `mark_as_paused()` sets DB state to PENDING but doesn't actually pause execution
- `_is_resuming` is a flag checked once in `initialize_db_tracking()`, not a proper state
- Subtask cancellation is not propagated — parent task must manually check each subtask
- No hierarchical pause: pausing a parent does not pause its children
- `keep_alive()` and `check_cancel` are loosely connected to lifecycle

**New design** — formal `TaskState` enum + state machine in `BaseTask`:

```python
class TaskState(str, Enum):
    """Task lifecycle states with well-defined transitions."""
    PENDING = "pending"         # Created, not yet started
    RUNNING = "running"         # Actively executing
    PAUSED = "paused"           # Execution suspended, context saved, can resume
    COMPLETED = "completed"     # Finished successfully
    FAILED = "failed"           # Finished with error
    CANCELLED = "cancelled"     # Cancelled by user/parent/timeout
    TIMED_OUT = "timed_out"     # Exceeded timeout

# Valid transitions
TASK_TRANSITIONS = {
    TaskState.PENDING:   {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING:   {TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMED_OUT, TaskState.PENDING},  # PENDING = recovery only
    TaskState.PAUSED:    {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),  # Terminal
    TaskState.FAILED:    {TaskState.PENDING},  # Can retry → back to PENDING
    TaskState.CANCELLED: set(),  # Terminal
    TaskState.TIMED_OUT: {TaskState.PENDING},  # Can retry → back to PENDING
}
```

**State machine in BaseTask**:
```python
class BaseTask(Generic[ConfigT], ...):
    _state: TaskState = TaskState.PENDING
    _state_lock: threading.RLock
    _children: list["BaseTask"]  # Tracked subtasks
    _parent: Optional["BaseTask"] = None

    def _transition(self, new_state: TaskState):
        """Thread-safe state transition with validation. No DB write — persist at flush points only."""
        with self._state_lock:
            if new_state not in TASK_TRANSITIONS[self._state]:
                raise InvalidStateTransition(self._state, new_state)
            old_state = self._state
            self._state = new_state
            # No _persist_state() here — persist only at checkpoint(), save_context(), terminal states
            logger.info(f"[{self.task_id}] {old_state} → {new_state}")

    @property
    def state(self) -> TaskState:
        return self._state

    # --- Lifecycle operations ---

    def start(self):
        self._transition(TaskState.RUNNING)

    def complete(self, result: str):
        self._transition(TaskState.COMPLETED)
        self.result = result
        self._persist_state()

    def fail(self, result: str):
        self._transition(TaskState.FAILED)
        self.result = result
        self._persist_state()

    def cancel(self, reason: str = ""):
        """Cancel this task AND all its children (hierarchical)."""
        with self._state_lock:
            self._transition(TaskState.CANCELLED)
            self.result = reason or "Cancelled"
            self._pause_event.set()  # Wake any paused checkpoint() wait
            children = list(self._children)  # Snapshot under lock
        for child in children:
            if child.state in (TaskState.RUNNING, TaskState.PAUSED, TaskState.PENDING):
                child.cancel(reason=f"Parent {self.task_id} cancelled")

    def pause(self):
        """Pause this task AND all its children. Saves context for resume."""
        self.tracking.save_context()
        with self._state_lock:
            self._transition(TaskState.PAUSED)
            children = list(self._children)  # Snapshot under lock
        for child in children:
            if child.state == TaskState.RUNNING:
                child.pause()

    def resume(self):
        """Resume from PAUSED state. Loads saved context."""
        self._transition(TaskState.RUNNING)
        context, stage = self.tracking.load_context()
        self._on_resume(context, stage)  # Hook for subclasses
        for child in self._children:
            if child.state == TaskState.PAUSED:
                child.resume()

    def retry(self):
        """Retry from FAILED/TIMED_OUT state. Resets to PENDING."""
        self._transition(TaskState.PENDING)
```

**Hierarchical subtask tracking**:
```python
# In SubtaskMixin
async def submit_and_wait_subtask(self, service_name, task, wait=True):
    task._parent = self                # Link parent
    self._children.append(task)        # Track child
    task_id = await manager.submit_task(service_name, task, ...)
    if wait:
        await manager.wait_for_task(task_id)
    return task_id
```

**Cooperative pause via checkpoint** (in `LifecycleManager`):
```python
async def checkpoint(self):
    """Check if task should pause/cancel. Call between stages of work.
    Deadlock-safe: lock is NOT held during the pause wait."""
    with self._task._state_lock:
        if self._task._state == TaskState.CANCELLED:
            raise TaskCancelled(self._task.task_id)
        if self._pause_requested:
            self._pause_requested = False
            self._transition(TaskState.PAUSED)  # Under lock — atomic
    # Wait OUTSIDE the lock — resume() and cancel() can acquire it
    if self._task._state == TaskState.PAUSED:
        await asyncio.get_event_loop().run_in_executor(None, self._pause_event.wait)
        # Re-check state: may have been cancelled while paused
        with self._task._state_lock:
            if self._task._state == TaskState.CANCELLED:
                raise TaskCancelled(self._task.task_id)
            if self._task._state == TaskState.PAUSED:
                self._transition(TaskState.RUNNING)
            # else: already resumed by another path
```

**Uniform lifecycle management — BaseTask owns ALL state transitions**:

The key design principle: **concrete tasks ONLY implement `_execute()`** (the business logic). They never call `complete()`, `fail()`, or `cancel()` directly. The base class wraps `_execute()` and manages all state transitions uniformly.

```python
class TaskResultStatus(str, Enum):
    """Predefined result statuses — no raw strings."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"  # Some work done, some failed
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

@dataclass
class TaskResult:
    """Typed task result — replaces raw string results."""
    status: TaskResultStatus
    message: str = ""                    # Human-readable description
    data: dict | None = None             # Optional structured result data
    error: Exception | None = None       # Original exception if failed
    metrics: TaskMetrics | None = None    # Typed: duration, tokens, retries

class BaseTask(Generic[ConfigT], ...):
    result: TaskResult | None = None

    # --- This is what BaseTask manages uniformly ---
    # NOTE: Worker threads MUST use contextvars.copy_context().run(task._run_wrapper)
    # to propagate ActivityContext and locale. See BaseService dispatch.

    async def run_async(self):
        """Testable entry point — runs lifecycle within an existing event loop."""
        self.lifecycle._transition(TaskState.RUNNING)
        self.progress.report(0, t("task.progress.starting"))
        try:
            result = await asyncio.wait_for(
                self._execute(),
                timeout=self.task_timeout_seconds,  # Enforced by asyncio, not threading.Timer
            )
            self.result = result
            if result.status in (TaskResultStatus.SUCCESS, TaskResultStatus.PARTIAL_SUCCESS):
                self.lifecycle._transition(TaskState.COMPLETED)
            else:
                self.lifecycle._transition(TaskState.FAILED)
        except asyncio.TimeoutError:
            self.result = TaskResult(status=TaskResultStatus.TIMED_OUT, message=t("task.result.timed_out"))
            self.lifecycle._transition(TaskState.TIMED_OUT)
        except TaskCancelled:
            self.result = TaskResult(status=TaskResultStatus.CANCELLED, message=t("task.result.cancelled"))
            self.lifecycle._transition(TaskState.CANCELLED)
        except Exception as e:
            logger.exception(f"Task {self.task_id} failed with unhandled exception")
            self.result = TaskResult(status=TaskResultStatus.FAILED, message=str(e), error=e)
            self.lifecycle._transition(TaskState.FAILED)
        finally:
            self.tracking.persist_final_state(self.result)

    def _run_wrapper(self):
        """Thread entry point. Creates event loop, delegates to run_async()."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_async())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # Architectural choice: Each task gets its own event loop in its own thread.
    # This prevents one task's async errors from crashing others, at the cost of
    # not sharing async connection pools. For scale, consider a shared event loop
    # with asyncio.run_coroutine_threadsafe().

    # --- This is ALL a concrete task implements ---
    @abstractmethod
    async def _execute(self) -> TaskResult:
        """
        Implement task-specific logic. Return a TaskResult.

        Rules:
            - Return TaskResult to indicate outcome (never call _complete/_fail/_cancel)
            - Use self.progress.report() for visibility
            - Use self.lifecycle.checkpoint() between stages for pause/cancel
            - For recovery: call self.tracking.load_context() at the top
            - Use self.tracking.save_context() to enable crash recovery
        """
        raise NotImplementedError
```

**Concrete task example — simple (no recovery)**:
```python
class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        dal = get_context().dal
        parsed = await self._parse_file()
        self.progress.report(30, t("task.progress.parsing_file"))

        problems = await self._extract_problems(parsed)
        self.progress.report(70, t("task.progress.extracted", count=len(problems)))
        await self.lifecycle.checkpoint()

        dal.exams.save_problems(self.config.exam_id, problems)
        self.progress.report(100, t("task.progress.complete"))

        return TaskResult(
            status=TaskResultStatus.SUCCESS,
            message=t("task.progress.extracted", count=len(problems)),
            data=ExamIngestResultData(problem_count=len(problems), exam_id=self.config.exam_id),
        )
```

**Concrete task example — with crash recovery (opt-in)**:
```python
class LongRunningIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        dal = get_context().dal
        context, stage = self.tracking.load_context()  # Opt-in recovery

        if stage < 1:
            parsed = await self._parse_file()
            self.tracking.save_context({"parsed_data": parsed}, task_stage=1)
            self.progress.report(30, t("task.progress.parsing_file"))
            await self.lifecycle.checkpoint()

        if stage < 2:
            parsed = context.get("parsed_data", None) or await self._parse_file()
            problems = await self._extract_problems(parsed)
            self.tracking.save_context({"problem_count": len(problems)}, task_stage=2)
            self.progress.report(70, t("task.progress.extracted", count=len(problems)))
            await self.lifecycle.checkpoint()

        dal.exams.save_problems(self.config.exam_id, problems)
        return TaskResult(status=TaskResultStatus.SUCCESS, message="Done")
```

**What concrete tasks DON'T do** (all handled by base):
- Never call `complete()`, `fail()`, `cancel()` — return `TaskResult` instead
- Never manage state transitions — base class does it
- Never handle `TaskCancelled`/`TaskTimedOut` — base class catches them
- Never set up event loops or threads — base class does it
- Never persist state directly — base class does it after `_execute()` returns

**DB persistence**: Every state transition calls `_persist_state()` which updates the task record.

#### Server crash recovery — automatic task lifecycle management

When the server crashes and restarts, orphaned tasks (still in `RUNNING` or `PAUSED` state in DB) need to be handled. This is managed by `TaskRecoveryManager`, invoked during server startup.

**File**: `src/services/recovery.py`

```python
@dataclass
class RecoveryPolicy:
    """Configurable recovery policy for orphaned tasks."""
    max_staleness: timedelta = timedelta(hours=1)     # Tasks older than this are abandoned, not recovered
    heartbeat_timeout: timedelta = timedelta(minutes=2)  # No heartbeat for this long = orphaned
    max_recovery_attempts: int = 3                      # After N recovery attempts, mark as FAILED
    auto_recover_states: set[TaskState] = field(
        default_factory=lambda: {TaskState.RUNNING, TaskState.PAUSED}
    )

class TaskRecoveryManager:
    """Handles task recovery after server restart."""

    def __init__(self, dal: DataAccessLayer, service_manager: ServiceManager, policy: RecoveryPolicy = RecoveryPolicy()):
        self.dal = dal
        self.service_manager = service_manager
        self.policy = policy

    async def recover_on_startup(self):
        """
        Called once during server startup. Scans DB for orphaned tasks and handles them.

        Recovery flow:
        1. Query all tasks in RUNNING or PAUSED state
        2. For each task, determine if it's recoverable:
           a. If last_heartbeat is too old (> heartbeat_timeout) AND task age < max_staleness → orphaned, attempt recovery
           b. If task age > max_staleness → too stale, mark as FAILED
           c. If recovery_attempts >= max_recovery_attempts → exhausted retries, mark as FAILED
        3. For recoverable tasks:
           a. Load saved context and stage from DB
           b. Reconstruct task from config + context
           c. Set state to PENDING, increment recovery_attempts
           d. Re-submit to ServiceManager → task resumes from last checkpoint
        """
        orphaned_tasks = self.dal.tasks.get_tasks_by_states(
            states=[s.value for s in self.policy.auto_recover_states]
        )

        now = get_utcnow()
        recovered = 0
        abandoned = 0

        for task_record in orphaned_tasks:
            age = now - task_record.created_at
            heartbeat_age = now - task_record.last_heartbeat if task_record.last_heartbeat else age

            # Too stale — abandon
            if age > self.policy.max_staleness:
                self.dal.tasks.update_state(
                    task_record.task_id, TaskState.FAILED.value,
                    message=f"Abandoned: task too stale ({age})"
                )
                abandoned += 1
                continue

            # Too many recovery attempts — abandon
            if task_record.recovery_attempts >= self.policy.max_recovery_attempts:
                self.dal.tasks.update_state(
                    task_record.task_id, TaskState.FAILED.value,
                    message=f"Abandoned: exceeded max recovery attempts ({self.policy.max_recovery_attempts})"
                )
                abandoned += 1
                continue

            # Heartbeat still fresh — might still be running in another process (skip)
            if heartbeat_age < self.policy.heartbeat_timeout:
                logger.info(f"Task {task_record.task_id} has fresh heartbeat, skipping recovery")
                continue

            # Recoverable — attempt recovery
            try:
                self._recover_task(task_record)
                recovered += 1
            except Exception as e:
                logger.error(f"Failed to recover task {task_record.task_id}: {e}")
                self.dal.tasks.update_state(
                    task_record.task_id, TaskState.FAILED.value,
                    message=f"Recovery failed: {e}"
                )
                abandoned += 1

        logger.info(f"Task recovery complete: {recovered} recovered, {abandoned} abandoned")

    def _recover_task(self, task_record: TaskSchema):
        """Reconstruct and re-submit a single task."""
        # Increment recovery attempts
        self.dal.tasks.increment_recovery_attempts(task_record.task_id)

        # Load the saved config and context
        config_data = task_record.config_snapshot  # JSON of BaseTaskConfig subclass
        context = task_record.context              # Saved checkpoint context
        stage = task_record.stage                  # Last completed stage

        # Reconstruct the task using the service's task factory
        service_name = task_record.service_name
        service = self.service_manager.get_service(service_name)
        task = service.reconstruct_task(
            task_id=task_record.task_id,
            config_data=config_data,
            context=context,
            stage=stage,
        )

        # Transition via state machine (RUNNING->PENDING is valid for recovery)
        task._transition(TaskState.PENDING)
        self.service_manager.queue_task_sync(service_name, task)
        logger.info(f"Recovered task {task_record.task_id} (service={service_name}, stage={stage})")
```

**DB schema additions for recovery**:
```python
# In TaskSchema / TaskModel
class TaskSchema(BaseSchema):
    task_id: int
    service_name: str
    state: str                          # TaskState value
    config_snapshot: dict | None        # Serialized BaseTaskConfig for reconstruction
    context: dict | None                # Last saved checkpoint context
    stage: int = 0                      # Last completed stage
    recovery_attempts: int = 0          # Number of recovery attempts
    last_heartbeat: datetime | None
    created_at: datetime
    message: str = ""
```

**BaseService must implement `reconstruct_task()`**:
```python
class BaseService:
    def reconstruct_task(self, task_id: int, config_data: dict, context: dict | None, stage: int) -> BaseTask:
        """Reconstruct a task from persisted state for recovery.

        Each service knows its task types and how to reconstruct them.
        The base implementation raises NotImplementedError — services that
        support recovery must override this.
        """
        raise NotImplementedError(
            f"Service {self.service_name} does not support task recovery. "
            f"Override reconstruct_task() to enable it."
        )
```

**Task creation is DB-first — task_id IS the DB record ID**:

Every task starts with a DB record. The DB record's auto-increment `id` becomes the `task_id`. No random UUIDs.

```python
class BaseTask:
    task_id: int  # NOT str, NOT UUID — this is the DB record's PK

    def __init__(self, config: ConfigT, service_name: str, model_overrides=None):
        """
        Create a task. Does NOT assign task_id — that happens in _create_db_record().
        """
        self.config = config
        self.service_name = service_name
        self._state = TaskState.PENDING
        self.task_id: int | None = None  # Set by _create_db_record() — will be set by _create_db_record()
        ...

    def _create_db_record(self) -> int:
        """
        Create the backing DB record. Returns the DB-generated task_id.
        Called by ServiceManager.submit_task() before the task starts running.
        This MUST be called before the task executes.
        """
        dal = get_context().dal
        record = dal.tasks.create(TaskCreateSchema(
            service_name=self.service_name,
            state=TaskState.PENDING.value,
            config_snapshot=self.config.model_dump(),
            config_type=type(self.config).__name__,
            user_id=self.config.user_id,
            parent_task_id=self._parent.task_id if self._parent else None,
        ))
        self.task_id = record.id  # DB-generated ID is the task ID
        return self.task_id

    def _persist_state(self):
        """Update the existing DB record with current state."""
        assert self.task_id is not None, "Task must have a DB record before persisting state"
        dal = get_context().dal
        dal.tasks.update_state(self.task_id, self._state.value, message=self._message)
```

**ServiceManager enforces DB-first creation**:
```python
class ServiceManager:
    async def submit_task(self, service_name, config, timeout=None, model_overrides=None) -> int:
        """Submit a task. Creates DB record first, returns task_id (= DB record ID)."""
        backend = self._get_backend(service_name)

        # For local backend: create task object, then DB record, then execute
        task = service.create_task(config=config, model_overrides=model_overrides)
        task_id = task._create_db_record()  # DB record created — task_id assigned

        if timeout:
            task.set_timeout(timeout)
        backend.queue_task(task)

        return task_id  # Return int, not str
```

**Recovery uses the same task_id**:
```python
# When recovering, the task already has a DB record
def _recover_task(self, task_record: TaskSchema):
    task = service.reconstruct_task(
        task_id=task_record.id,  # Same DB record ID
        config_data=task_record.config_snapshot,
        ...
    )
    task.task_id = task_record.id  # Reuse the same DB ID
    ...
```

**Benefits**:
- **Single source of truth**: task_id = DB record ID, always
- **No UUID management**: IDs are simple integers, DB-generated
- **Query friendly**: `dal.tasks.get_by_id(123)` — no UUID string parsing
- **Parent-child tracking**: `parent_task_id` foreign key in DB for subtask hierarchy
- **Enforced**: task_id is set only by `_create_db_record()` — no constructor assignment allowed

**Integration in server startup** (`base_server.py`):
```python
class BaseAPIServer:
    async def on_startup(self):
        config = get_config()
        init_db(config.database)
        setup_logger("edu", config)

        self.service_manager = ServiceManager()
        self.service_manager.start_all_services()

        # Recover orphaned tasks from previous crash
        recovery = TaskRecoveryManager(
            dal=get_dal(),
            service_manager=self.service_manager,
            policy=RecoveryPolicy(
                max_staleness=timedelta(hours=config.task_max_staleness_hours),
                max_recovery_attempts=config.task_max_recovery_attempts,
            ),
        )
        await recovery.recover_on_startup()
```

**Lifecycle summary**:
```
Task Created → PENDING → RUNNING (heartbeating) → COMPLETED/FAILED/CANCELLED
                                     |
                              [server crash]
                                     |
                              [server restart]
                                     |
                         TaskRecoveryManager scans DB
                                     |
                    ┌────────────────┼────────────────┐
                    │                │                │
              heartbeat fresh   recoverable      too stale
              (skip, still      (age < max,      (age > max OR
               running?)         attempts < max)  attempts >= max)
                                     |                │
                              reconstruct task   mark FAILED
                              PENDING → RUNNING
                              (resumes from last checkpoint)
```

**Hierarchical progress reporting**:

Progress should aggregate automatically when a task has subtasks. Each task declares its weight in the parent's progress.

```python
class BaseTask(Generic[ConfigT], ...):
    _progress: int = 0            # 0-100, this task's own progress
    _message: str = ""
    _children: list["BaseTask"]
    _child_weights: dict[str, float]  # task_id -> weight (0.0-1.0)

    def report_progress(self, progress: int, message: str):
        """Report this task's own progress. Triggers parent recalculation."""
        self._progress = progress
        self._message = message
        self._persist_progress()
        if self._parent:
            self._parent._recalculate_progress()

    def _recalculate_progress(self):
        """Recalculate aggregate progress from children + own work."""
        if not self._children:
            return  # Leaf task — progress is just self._progress

        # Weighted average of child progress
        total_weight = sum(self._child_weights.get(c.task_id, 1.0) for c in self._children)
        weighted_sum = sum(
            c._get_effective_progress() * self._child_weights.get(c.task_id, 1.0)
            for c in self._children
        )
        self._progress = int(weighted_sum / total_weight) if total_weight > 0 else 0
        self._message = self._build_aggregate_message()
        self._persist_progress()
        # Propagate up
        if self._parent:
            self._parent._recalculate_progress()

    def _get_effective_progress(self) -> int:
        """Get progress considering children."""
        if self._children:
            self._recalculate_progress()
        return self._progress

    def _build_aggregate_message(self) -> str:
        """Build a progress message showing subtask status."""
        running = [c for c in self._children if c.state == TaskState.RUNNING]
        if running:
            return f"{self._progress}% — {running[0]._message}"
        return self._message
```

**Usage in subtask submission**:
```python
async def submit_and_wait_subtask(self, service_name, task, weight=1.0, wait=True):
    task._parent = self
    self._children.append(task)
    self._child_weights[task.task_id] = weight
    task_id = await manager.submit_task(service_name, task, ...)
    if wait:
        await manager.wait_for_task(task_id)
    return task_id
```

**Example — multi-stage task with weighted subtasks**:
```python
class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        # Stage 1: Parse file (30% of total work)
        parse_task = ParseTask(config=..., service_name=SERVICE_PARSE)
        await self.submit_and_wait_subtask(SERVICE_PARSE, parse_task, weight=0.3)
        # Parent progress auto-updates as parse_task reports 0→100%

        await self.lifecycle.checkpoint()

        # Stage 2: Extract problems (50% of total work)
        extract_task = ExamExtractTask(config=..., service_name=SERVICE_EXAM_EXTRACT)
        await self.submit_and_wait_subtask(SERVICE_EXAM_EXTRACT, extract_task, weight=0.5)

        # Stage 3: Own work (20% — no subtask)
        self.progress.report(80, "Finalizing...")
        await self._finalize()
        self.progress.report(100, "Done")
        return TaskResult(status=TaskResultStatus.SUCCESS, message="Done")
```

The API endpoint can query a single task_id and get aggregated progress across the entire subtask tree, without needing to know about subtask structure.

**Key improvements over source**:
1. **Formal state enum** — no more boolean flags (`completed`, `cancelled`)
2. **Validated transitions** — can't go from COMPLETED to RUNNING
3. **Hierarchical propagation** — pause/cancel/resume cascade to all children
4. **Cooperative checkpoints** — tasks opt-in to pause points via `await self.lifecycle.checkpoint()`
5. **Stage-based resume** — `save_context(stage=N)` + `load_context()` in `_run()` enables pick-up-where-left-off
6. **Server recovery** — on restart, orphaned RUNNING tasks are detected via stale heartbeats
7. **Hierarchical progress** — parent progress auto-aggregates from weighted children, propagates up the tree

### 9. Task-aware AI model conversation with progress, cancellation, and recovery

**Source problem**: `AIConversationBase.run_chat_completion()` is a black box:
- The tool-calling loop (`while response_message.tool_calls`) runs indefinitely with no progress reporting
- No cancellation check — if a task is cancelled, the model call keeps running until it finishes
- No way to resume a multi-turn conversation that was interrupted
- No token/cost tracking per task
- Async version (`run_chat_completion_async`) has the same issues

**New design** — `TaskConversation` wrapper that integrates `AIConversationBase` with the task lifecycle:

**File**: `src/models/task_conversation.py`

```python
class ConversationState(BaseModel):
    """Serializable snapshot of a conversation for persistence/recovery."""
    messages: list[dict]       # Serialized message history
    system_prompt: str | None
    tool_names: list[str]      # Tool names (tools reconstructed from names)
    model_class: str           # e.g. "openai:gpt-4o"
    turn_count: int = 0        # Number of completed model turns
    total_input_tokens: int = 0
    total_output_tokens: int = 0

class TaskConversation:
    """Wraps AIConversationBase with task lifecycle integration."""

    def __init__(
        self,
        task: BaseTask,
        conversation: AIConversationBase,
        label: str = "",           # Human-readable label e.g. "extract_problems"
        max_turns: int = 20,       # Safety limit on tool-calling loops
    ):
        self.task = task
        self.conversation = conversation
        self.label = label
        self.max_turns = max_turns
        self.turn_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def run(self, user_prompt: str | None = None) -> str:
        """Run conversation with task-aware progress, cancellation, and tracking."""
        if user_prompt:
            self.conversation.messages.append(
                self.conversation._create_user_prompt_message(user_prompt)
            )

        response = await self.conversation.model.handle_chat_completion_request_async(
            messages=self.conversation.messages,
            tools=self.conversation.tools,
        )
        self._track_usage(response)

        while response.tool_calls:
            self.turn_count += 1

            # --- Cancellation check between turns ---
            await self.task.lifecycle.checkpoint()

            # --- Safety limit ---
            if self.turn_count >= self.max_turns:
                raise ConversationTurnLimitExceeded(self.label, self.max_turns)

            # --- Progress reporting ---
            tool_names = [tc.tool_name for tc in response.tool_calls]
            self.task.progress.report(
                self.task._progress,  # Don't change overall %, just update message
                f"[{self.label}] Turn {self.turn_count}: calling {', '.join(tool_names)}"
            )

            # --- Execute tools ---
            self.conversation.messages.append(response)
            for tool_call in response.tool_calls:
                tool_result = self.conversation._call_tool(
                    tool_call_id=tool_call.tool_call_id,
                    tool_name=tool_call.tool_name,
                    params=tool_call.tool_params,
                )
                self.conversation.messages.append(
                    self.conversation._create_tool_result_message(
                        tool_call_id=tool_call.tool_call_id,
                        tool_name=tool_call.tool_name,
                        tool_result=tool_result,
                        tool_params=tool_call.tool_params,
                    )
                )

            # --- Next model call ---
            response = await self.conversation.model.handle_chat_completion_request_async(
                messages=self.conversation.messages,
                tools=self.conversation.tools,
            )
            self._track_usage(response)

        self.conversation.messages.append(response)
        self.conversation.last_model_response = response.content
        return response.content

    def snapshot(self) -> ConversationState:
        """Serialize conversation state for DB persistence / recovery."""
        return ConversationState(
            messages=[m.serialize() for m in self.conversation.messages],
            system_prompt=self.conversation.system_prompt,
            tool_names=[t.name for t in (self.conversation.tools or [])],
            model_class=self.conversation.model.model_class,
            turn_count=self.turn_count,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
        )

    @classmethod
    def from_snapshot(cls, task: BaseTask, state: ConversationState, tools: list[AIToolBase]) -> "TaskConversation":
        """Reconstruct conversation from saved state for resumption."""
        model = task.get_model_for_scenario(...)  # Recreate model
        conversation = model.create_conversation(system_prompt=state.system_prompt, tools=tools)
        conversation.messages = [...]  # Deserialize messages
        tc = cls(task=task, conversation=conversation)
        tc.turn_count = state.turn_count
        tc.total_input_tokens = state.total_input_tokens
        tc.total_output_tokens = state.total_output_tokens
        return tc

    def _track_usage(self, response):
        """Track token usage from model response."""
        if hasattr(response, 'usage') and response.usage:
            self.total_input_tokens += response.usage.get('input_tokens', 0)
            self.total_output_tokens += response.usage.get('output_tokens', 0)
```

**Usage in a task**:
```python
class ExamAnalysisTask(BaseTask[ExamAnalysisTaskConfig]):
    async def _execute(self) -> TaskResult:
        context, stage = self.tracking.load_context()

        if stage < 1:
            model = self.get_model_for_scenario(CONTENT_EXTRACTION)
            conv = model.create_conversation(system_prompt="...", tools=[...])
            tc = TaskConversation(task=self, conversation=conv, label="extract_answers")

            result = await tc.run(user_prompt="Analyze this answer sheet...")
            # Conversation state saved as part of task context
            self.tracking.save_context({"extraction": result, "conv_state": tc.snapshot().model_dump()}, task_stage=1)
            await self.lifecycle.checkpoint()

        if stage < 2:
            # Stage 2 can resume the conversation if needed
            if "conv_state" in context:
                tc = TaskConversation.from_snapshot(self, ConversationState(**context["conv_state"]), tools=[...])
            ...
```

**Key improvements**:
1. **Cancellation between turns** — `await self.task.lifecycle.checkpoint()` after every tool-calling round; if task is cancelled/paused, the conversation stops cleanly
2. **Progress visibility** — each model turn updates the task's message with tool names being called
3. **Recovery** — `snapshot()` / `from_snapshot()` lets a paused/failed task resume a multi-turn conversation from where it left off
4. **Token tracking** — per-conversation input/output token counts, aggregated at the task level
5. **Safety limit** — `max_turns` prevents infinite tool-calling loops
6. **Original `AIConversationBase` unchanged** — `TaskConversation` is a wrapper, not a replacement. Non-task code (scripts, testing) can still use `AIConversationBase` directly

### 10. Built-in retry/resilience for tasks and AI calls

**Source problem**: No generic retry support. Every service that calls an AI model or external API writes its own try/except with ad-hoc retry logic (or worse, no retry at all). Common transient failures (API rate limits, timeouts, network errors) cause task failures unnecessarily.

**New design** — two layers of retry support:

#### Layer 1: `RetryPolicy` — configurable, reusable retry strategy

**File**: `src/utilities/retry.py`

```python
@dataclass
class RetryPolicy:
    """Configurable retry strategy."""
    max_retries: int = 3
    base_delay: float = 1.0           # Seconds
    max_delay: float = 60.0           # Cap on backoff
    backoff_factor: float = 2.0       # Exponential backoff multiplier
    jitter: bool = True               # Add randomness to prevent thundering herd
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    retryable_status_codes: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()  # 50-150% of calculated delay
        return delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        # Check exception type
        if isinstance(error, self.retryable_exceptions):
            return True
        # Check HTTP status codes (for API errors)
        if hasattr(error, 'status_code') and error.status_code in self.retryable_status_codes:
            return True
        return False

# Pre-built policies
RETRY_AI_CALL = RetryPolicy(max_retries=3, base_delay=2.0, backoff_factor=2.0)
RETRY_EXTERNAL_API = RetryPolicy(max_retries=5, base_delay=1.0, max_delay=30.0)
RETRY_DB_OPERATION = RetryPolicy(max_retries=2, base_delay=0.5, backoff_factor=1.5)
NO_RETRY = RetryPolicy(max_retries=0)

async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args,
    policy: RetryPolicy = RETRY_AI_CALL,
    task: BaseTask | None = None,      # Optional task for cancellation checks
    on_retry: Callable | None = None,  # Hook called before each retry
    **kwargs,
) -> T:
    """Execute an async function with retry support."""
    last_error = None
    for attempt in range(policy.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if not policy.should_retry(e, attempt):
                raise
            delay = policy.get_delay(attempt)
            logger.warning(
                f"Retry {attempt+1}/{policy.max_retries} after {delay:.1f}s: {type(e).__name__}: {e}"
            )
            if on_retry:
                on_retry(attempt, e, delay)
            # Check task cancellation before sleeping
            if task:
                await task.lifecycle.checkpoint()
            await asyncio.sleep(delay)
    raise last_error  # Should not reach here, but safety net
```

#### Layer 2: Integrated into `TaskConversation` and `BaseTask`

**TaskConversation** automatically retries model calls:
```python
class TaskConversation:
    def __init__(self, ..., retry_policy: RetryPolicy = RETRY_AI_CALL):
        self.retry_policy = retry_policy

    async def run(self, user_prompt=None) -> str:
        ...
        # Each model call is wrapped with retry
        response = await retry_async(
            self.conversation.model.handle_chat_completion_request_async,
            messages=self.conversation.messages,
            tools=self.conversation.tools,
            policy=self.retry_policy,
            task=self.task,
            on_retry=lambda attempt, e, delay: self.task.progress.report(
                self.task._progress,
                f"[{self.label}] Retrying model call ({attempt+1}/{self.retry_policy.max_retries}): {e}"
            ),
        )
        ...
```

**BaseTask** provides a `run_with_retry()` helper for subtask submission:
```python
class BaseTask:
    async def run_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        policy: RetryPolicy = RETRY_AI_CALL,
        label: str = "",
        **kwargs,
    ) -> T:
        """Run any async function with retry, integrated with task lifecycle."""
        return await retry_async(
            func, *args,
            policy=policy,
            task=self,
            on_retry=lambda attempt, e, delay: self.progress.report(
                self._progress,
                f"[{label}] Retry {attempt+1}: {e}"
            ),
            **kwargs,
        )
```

**Usage in concrete tasks**:
```python
class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        # AI call — automatically retries on rate limit / timeout
        model = self.get_model_for_scenario(CONTENT_EXTRACTION)
        conv = model.create_conversation(system_prompt="...", tools=[...])
        tc = TaskConversation(task=self, conversation=conv, label="extract")
        result = await tc.run("Extract problems from this document...")

        # External API call — custom retry policy
        file_url = await self.run_with_retry(
            self._upload_to_s3, file_bytes,
            policy=RETRY_EXTERNAL_API,
            label="s3_upload",
        )

        # DB operation — minimal retry
        await self.run_with_retry(
            self._save_results, result,
            policy=RETRY_DB_OPERATION,
            label="save_results",
        )
```

**Key features**:
1. **Generic** — `retry_async()` works with any async function, not just AI calls
2. **Policy-based** — pre-built policies for common scenarios (AI, external API, DB); tasks can customize
3. **Task-integrated** — checks `task.lifecycle.checkpoint()` between retries (cancellation-aware)
4. **Progress-aware** — retry attempts show in task progress messages
5. **Exponential backoff + jitter** — prevents thundering herd on shared APIs
6. **Composable** — `TaskConversation` uses it internally, tasks use `run_with_retry()` for anything else

### 11. Domain exception hierarchy (replaces bare `except:`)

**Source problem**: 15+ instances of bare `except:` or `except Exception:` that swallow all errors including `SystemExit` and `KeyboardInterrupt`. Error context is lost — only `str(e)` is logged, losing exception type and traceback. No domain-specific exceptions — everything is generic.

**New** (`src/exceptions.py`):
```python
class EduBaseError(Exception):
    """Base for all application exceptions."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

# --- Task layer ---
class TaskError(EduBaseError): pass
class TaskCancelled(TaskError): pass
class TaskTimedOut(TaskError): pass
class InvalidStateTransition(TaskError):
    def __init__(self, from_state, to_state):
        super().__init__(f"Invalid transition: {from_state} → {to_state}")
class ConversationTurnLimitExceeded(TaskError): pass

# --- AI model layer ---
class AIModelError(EduBaseError): pass
class AIRateLimitError(AIModelError): pass
class AIAuthenticationError(AIModelError): pass
class AIContextLengthExceeded(AIModelError): pass

# --- DB layer ---
class DatabaseError(EduBaseError): pass
class RecordNotFoundError(DatabaseError): pass
class DuplicateRecordError(DatabaseError): pass

# --- Service layer ---
class ServiceError(EduBaseError): pass
class ServiceNotFoundError(ServiceError): pass
class DependencyCycleError(ServiceError): pass

# --- Auth ---
class AuthError(EduBaseError): pass
class InvalidCredentialsError(AuthError): pass
class TokenExpiredError(AuthError): pass
class InsufficientPermissionsError(AuthError): pass

# --- File/storage ---
class StorageError(EduBaseError): pass
class StorageFileNotFoundError(StorageError): pass
class FileValidationError(StorageError): pass
```

**Rules**:
- Never use bare `except:` — always catch specific exception types
- Use `logger.exception()` (not `logger.error(str(e))`) to preserve traceback
- Each layer raises its own domain exceptions
- `RetryPolicy.retryable_exceptions` uses these types (e.g., `AIRateLimitError` is retryable, `AIAuthenticationError` is not)

### 12. Structured logging (replaces `print()` and logger-DB coupling)

**Source problems**:
- 5+ `print()` statements in production code (`database.py`, `base_server.py`)
- `utilities/__init__.py` imports DB models at module level for `DBHandler`, creating a circular dependency
- No structured logging — messages are freeform strings, hard to parse/search
- Logger initialized at import time with side effects

**New** (`src/utilities/logging.py`):
```python
import logging
import json
from typing import Any

class StructuredFormatter(logging.Formatter):
    """JSON-structured log output for production."""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra context if provided
        if hasattr(record, 'context'):
            log_data["context"] = record.context
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

class LazyDBHandler(logging.Handler):
    """DB logging handler that lazily imports DB dependencies."""
    _db_available = None

    def emit(self, record):
        if self._db_available is None:
            try:
                from db.operations.task_ops import create_log_entry
                self._db_available = True
            except ImportError:
                self._db_available = False
        if not self._db_available:
            return
        try:
            from db.operations.task_ops import create_log_entry
            create_log_entry(
                level=record.levelname,
                message=self.format(record),
                logger_name=record.name,
            )
        except Exception:
            pass  # DB logging is best-effort, never crash the app

def setup_logger(name: str = "edu", config: Any = None) -> logging.Logger:
    """Factory function — call explicitly, no import-time side effects."""
    ...
```

**Rules**:
- Zero `print()` in production code — use `logger` at appropriate level
- Logger setup is explicit via `setup_logger()`, not import-time
- `LazyDBHandler` imports DB dependencies only on first use (breaks circular dep)
- Use `logger.exception()` for errors (auto-includes traceback)

### 13. Replace singletons with Dependency Injection via Application Context

**Source problem**: `ServiceManager` and `ModelManager` use the singleton pattern (double-check locking, `__new__` override). This causes:
- **Testing pain**: Global state persists between tests — need to manually reset `_instance = None`
- **Hidden dependencies**: Any code can call `ServiceManager()` anywhere — no explicit wiring
- **Thread-safety complexity**: Double-check locking for creation + unprotected dict access after creation
- **Configuration inflexibility**: Can't create multiple instances with different configs (e.g., test vs prod)

**New approach** — an `AppContext` container that holds all shared instances, created once at startup and injected everywhere:

```python
# src/context.py
from dataclasses import dataclass

@dataclass
class AppContext:
    """Application-wide dependency container. Created once at startup, injected everywhere."""
    config: AppConfig
    dal: DataAccessLayer
    service_manager: "ServiceManager"
    model_manager: "ModelManager"

# Module-level holder — set once during startup, accessed via get_context()
_context: AppContext | None = None

def init_context(config: AppConfig) -> AppContext:
    """Initialize the application context. Called once during server startup."""
    global _context
    if _context is not None:
        raise RuntimeError("AppContext already initialized")

    dal = DataAccessLayer(session_factory=create_session_factory(config.database))
    model_manager = ModelManager(config.ai)
    service_manager = ServiceManager(dal=dal, model_manager=model_manager)

    _context = AppContext(
        config=config,
        dal=dal,
        service_manager=service_manager,
        model_manager=model_manager,
    )
    return _context

def get_context() -> AppContext:
    """Get the current application context. Raises if not initialized."""
    if _context is None:
        raise RuntimeError("AppContext not initialized — call init_context() first")
    return _context

def reset_context():
    """Reset context (for testing only)."""
    global _context
    _context = None
```

**ServiceManager and ModelManager are now plain classes** (no singleton):
```python
class ServiceManager:
    def __init__(self, dal: DataAccessLayer, model_manager: ModelManager):
        self.dal = dal
        self.model_manager = model_manager
        self._services: dict[str, BaseService] = {}
        self._state_lock = threading.RLock()
        ...
    # No __new__, no _instance, no double-check locking

class ModelManager:
    def __init__(self, ai_config: AIConfig):
        self._default_model = ai_config.openai_model or "gpt-4o"
        self._scenario_overrides: dict[str, str] = {}
        self._lock = threading.RLock()
        ...
    # No singleton pattern
```

**FastAPI integration** — inject via `Depends()`:
```python
# src/backend/dependencies.py
from context import get_context, AppContext

def get_app_context() -> AppContext:
    return get_context()

def get_dal() -> DataAccessLayer:
    return get_context().dal

def get_service_manager() -> ServiceManager:
    return get_context().service_manager

# In API endpoints
@app.post("/api/v1/tasks/submit")
async def submit_task(
    request: TaskSubmitRequest,
    sm: ServiceManager = Depends(get_service_manager),
):
    task_id = await sm.submit_task(request.service_name, request.config)
    return {"task_id": task_id}
```

**In tasks** — access via context instead of importing singleton:
```python
class BaseTask:
    def get_service_manager(self) -> ServiceManager:
        from context import get_context
        return get_context().service_manager

    def get_model_for_scenario(self, scenario: str) -> AIModelBase:
        from context import get_context
        manager = get_context().model_manager
        ...
```

**Server startup**:
```python
class BaseAPIServer:
    async def on_startup(self):
        config = get_config()
        init_db(config.database)
        ctx = init_context(config)  # Creates all managers
        ctx.service_manager.start_all_services()
        # Recovery, etc.
```

**Testing — the key benefit**:
```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def clean_context():
    """Reset app context between tests."""
    reset_context()
    yield
    reset_context()

@pytest.fixture
def app_context(test_config):
    """Create a fresh context for each test with test config."""
    return init_context(test_config)

@pytest.fixture
def mock_context():
    """Fully mocked context for unit tests."""
    ctx = AppContext(
        config=test_config,
        dal=MagicMock(spec=DataAccessLayer),
        service_manager=MagicMock(spec=ServiceManager),
        model_manager=MagicMock(spec=ModelManager),
    )
    # Monkey-patch get_context to return mock
    ...
```

**Thread safety**: Still need `RLock` on internal dicts within `ServiceManager` and `ModelManager`, but the creation complexity (double-check locking in `__new__`) is eliminated entirely.

**Why this is better than singletons**:
- **Testable**: `reset_context()` + fresh `init_context()` in each test — no leaked state
- **Explicit**: Dependencies are visible in `init_context()` wiring — no hidden globals
- **Configurable**: Different tests can use different configs without env var hacks
- **Simple**: Plain classes with constructor injection — no metaclass tricks

### 14. No star imports, no import-time DB/env coupling

**Source problems**:
- `from db.db_models import *` in `conftest.py` and `alembic/env.py`
- `env_vars/__init__.py` calls `dotenv.load_dotenv()` and reads all env vars at import time
- `utilities/__init__.py` creates logger + handlers at import time (including DB handler)

**Rules for the new project**:
- All imports are explicit — no `from x import *`
- No module-level side effects — no `load_dotenv()`, no `create_engine()`, no handler setup at import time
- Initialization is explicit via factory functions called during startup:
  1. `config = get_config()` — loads .env, validates
  2. `init_db(config.database)` — creates engine
  3. `setup_logger("edu", config)` �� configures handlers
  4. `ServiceManager(config)` — initializes services

### 16. Localization support for user-facing strings

**Source problem**: All user-facing strings (error messages, progress messages, API responses) are hardcoded in English with no localization path.

**New** (`src/i18n/`):

```
src/i18n/
├���─ __init__.py           # t() function, locale management
├── locales/
│   ├── en.json           # English (default)
│   └── zh.json           # Chinese
```

**Design** — simple key-based translation with interpolation:

```python
# src/i18n/__init__.py
import json
from pathlib import Path
from threading import local

_thread_local = local()
_translations: dict[str, dict[str, str]] = {}  # locale -> {key: translated_string}
_default_locale = "en"

def load_locales(locale_dir: Path | None = None):
    """Load all locale JSON files. Called once at startup."""
    if locale_dir is None:
        locale_dir = Path(__file__).parent / "locales"
    for file in locale_dir.glob("*.json"):
        locale = file.stem  # "en", "zh", etc.
        _translations[locale] = json.loads(file.read_text(encoding="utf-8"))

def set_locale(locale: str):
    """Set locale for the current thread/request."""
    _thread_local.locale = locale

def get_locale() -> str:
    """Get current locale (defaults to 'en')."""
    return getattr(_thread_local, 'locale', _default_locale)

def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current locale.

    Args:
        key: Dot-separated key (e.g., "task.progress.parsing_file")
        **kwargs: Interpolation values (e.g., count=5)

    Returns:
        Translated string with interpolation applied.
        Falls back to English if key not found in current locale.
        Falls back to the key itself if not found anywhere.

    Example:
        t("auth.invalid_credentials")  # "Invalid username or password"
        t("task.progress.extracted", count=5)  # "Extracted 5 problems"
    """
    locale = get_locale()
    # Try current locale, fall back to default, fall back to key
    text = _translations.get(locale, {}).get(key)
    if text is None:
        text = _translations.get(_default_locale, {}).get(key)
    if text is None:
        return key  # Key itself as fallback
    if kwargs:
        text = text.format(**kwargs)
    return text
```

**Locale files**:
```json
// src/i18n/locales/en.json
{
    "auth.invalid_credentials": "Invalid username or password",
    "auth.token_expired": "Your session has expired, please log in again",
    "auth.insufficient_permissions": "You do not have permission to perform this action",
    "task.progress.starting": "Starting...",
    "task.progress.parsing_file": "Parsing file...",
    "task.progress.extracted": "Extracted {count} problems",
    "task.progress.complete": "Complete",
    "task.result.success": "Task completed successfully",
    "task.result.cancelled": "Task was cancelled",
    "task.result.timed_out": "Task timed out",
    "task.result.failed": "Task failed: {reason}",
    "exam.not_found": "Exam not found",
    "exam.no_access": "You do not have access to this exam",
    "file.upload_failed": "File upload failed: {reason}",
    "file.invalid_type": "Unsupported file type: {type}"
}
```

```json
// src/i18n/locales/zh.json
{
    "auth.invalid_credentials": "用户名或密码错误",
    "auth.token_expired": "会话已过期，请重新登录",
    "auth.insufficient_permissions": "您没有权限执行此操作",
    "task.progress.starting": "开始...",
    "task.progress.parsing_file": "正在解析文件...",
    "task.progress.extracted": "已提取 {count} 道题目",
    "task.progress.complete": "完成",
    "task.result.success": "任务完成",
    "task.result.cancelled": "任务已取消",
    "task.result.timed_out": "任务超时",
    "task.result.failed": "任务失败：{reason}",
    "exam.not_found": "未找到考试",
    "exam.no_access": "您没有访问此考试的权限",
    "file.upload_failed": "文件上传失败：{reason}",
    "file.invalid_type": "不支持的文件类型：{type}"
}
```

**FastAPI integration** — set locale per-request from `Accept-Language` header:
```python
# src/backend/dependencies.py
from i18n import set_locale

async def set_request_locale(request: Request):
    """FastAPI dependency that sets locale from Accept-Language header."""
    accept_lang = request.headers.get("Accept-Language", "en")
    locale = accept_lang.split(",")[0].split("-")[0].strip()  # "zh-CN" → "zh"
    set_locale(locale)

# In BaseAPIServer setup:
app.add_middleware(...)  # Or as a dependency on all routes
```

**Usage everywhere**:
```python
# In API endpoints
from i18n import t
raise HTTPException(status_code=401, detail=t("auth.invalid_credentials"))

# In tasks
self.progress.report(30, t("task.progress.parsing_file"))
return TaskResult(
    status=TaskResultStatus.SUCCESS,
    message=t("task.progress.extracted", count=len(problems)),
)

# In exceptions
class InvalidCredentialsError(AuthError):
    def __init__(self):
        super().__init__(t("auth.invalid_credentials"))
```

**Rules**:
- ALL user-facing strings use `t("key")` — never hardcoded
- Internal log messages remain in English (not localized — these are for developers)
- `TaskResult.message` uses `t()` since it may be shown to users
- `logger.info()` / `logger.error()` stay in English
- New locale files can be added by dropping a JSON file into `locales/`

### 17. Local/remote service transparency — unified task execution API

**Source problem**: `ServiceManager` has a `_remote_services: dict[str, str]` field for remote endpoints, but:
- No actual remote execution implementation exists
- No protocol defined for how remote tasks communicate
- Callers would need to know if a service is local or remote to call it differently
- No serialization of tasks for wire transport

**New design** — abstract `ServiceBackend` interface that `ServiceManager` delegates to. Local and remote are just two implementations of the same interface.

**File**: `src/service_management/backends/`

```
src/service_management/
├── __init__.py
├── service_manager.py          # ServiceManager (delegates to backends)
└── backends/
    ├── __init__.py
    ├── base.py                 # ServiceBackend protocol
    ├── local_backend.py        # LocalServiceBackend (current behavior)
    └── remote_backend.py       # RemoteServiceBackend (HTTP-based)
```

**ServiceBackend protocol**:
```python
# src/service_management/backends/base.py
from typing import Protocol

class ServiceBackend(Protocol):
    """Abstract interface for executing tasks on a service — local or remote."""

    async def submit_task(
        self,
        service_name: str,
        config: BaseTaskConfig,
        task_id: int | None = None,
        timeout: float | None = None,
        model_overrides: dict[str, str] | None = None,
    ) -> str:
        """Submit a task. Returns task_id."""
        ...

    async def wait_for_task(self, task_id: int, timeout: float | None = None) -> TaskResult:
        """Wait for task completion. Returns TaskResult."""
        ...

    async def get_task_status(self, task_id: int) -> TaskStatusResponse:
        """Get current task state and progress."""
        ...

    async def cancel_task(self, task_id: int) -> bool:
        """Request task cancellation."""
        ...

    async def pause_task(self, task_id: int) -> bool:
        """Request task pause."""
        ...

    async def resume_task(self, task_id: int) -> bool:
        """Request task resume."""
        ...

@dataclass
class TaskStatusResponse:
    task_id: int
    state: TaskState
    progress: int
    message: str
    result: TaskResult | None = None
```

**LocalServiceBackend** — wraps the current in-process execution:
```python
class LocalServiceBackend:
    """Executes tasks in-process using the local service registry."""

    def __init__(self, service_manager: "ServiceManager"):
        self._manager = service_manager

    async def submit_task(self, service_name, config, task_id=None, timeout=None, model_overrides=None) -> str:
        service = self._manager.get_service(service_name)
        task = service.create_task(config=config, task_id=task_id, model_overrides=model_overrides)
        service.queue_task(task)
        if timeout:
            task.set_timeout(timeout)
        return task.task_id

    async def wait_for_task(self, task_id, timeout=None) -> TaskResult:
        # ... existing wait logic using futures
        ...

    async def get_task_status(self, task_id) -> TaskStatusResponse:
        task = self._manager._get_tracked_task(task_id)
        return TaskStatusResponse(
            task_id=task_id,
            state=task.state,
            progress=task._progress,
            message=task._message,
            result=task.result,
        )

    async def cancel_task(self, task_id) -> bool:
        task = self._manager._get_tracked_task(task_id)
        task.cancel()
        return True
```

**RemoteServiceBackend** — delegates to a remote server via HTTP:
```python
class RemoteServiceBackend:
    """Executes tasks on a remote service via HTTP API."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=30.0,
        )

    async def submit_task(self, service_name, config, task_id=None, timeout=None, model_overrides=None) -> str:
        response = await self._client.post(
            "/api/v1/tasks/submit",
            json={
                "service_name": service_name,
                "config": config.model_dump(),           # BaseTaskConfig is Pydantic — serializable
                "config_type": type(config).__name__,    # For deserialization on remote end
                "task_id": task_id,
                "timeout": timeout,
                "model_overrides": model_overrides,
            },
        )
        response.raise_for_status()
        return response.json()["task_id"]

    async def wait_for_task(self, task_id, timeout=None) -> TaskResult:
        """Poll for task completion."""
        deadline = time.time() + timeout if timeout else None
        while True:
            status = await self.get_task_status(task_id)
            if status.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMED_OUT):
                return status.result
            if deadline and time.time() > deadline:
                raise TaskTimedOut(f"Timed out waiting for remote task {task_id}")
            await asyncio.sleep(1.0)  # Poll interval

    async def get_task_status(self, task_id) -> TaskStatusResponse:
        response = await self._client.get(f"/api/v1/tasks/{task_id}/status")
        response.raise_for_status()
        data = response.json()
        return TaskStatusResponse(**data)

    async def cancel_task(self, task_id) -> bool:
        response = await self._client.post(f"/api/v1/tasks/{task_id}/cancel")
        return response.status_code == 200
```

**ServiceManager uses backends**:
```python
class ServiceManager:
    def __init__(self):
        ...
        self._backends: dict[str, ServiceBackend] = {}  # service_name -> backend
        self._default_backend = LocalServiceBackend(self)

    def register_remote_service(self, service_name: str, base_url: str, api_key: str | None = None):
        """Register a service as remote — tasks will be sent via HTTP."""
        self._backends[service_name] = RemoteServiceBackend(base_url, api_key)

    def _get_backend(self, service_name: str) -> ServiceBackend:
        return self._backends.get(service_name, self._default_backend)

    async def submit_task(self, service_name, config, task_id=None, timeout=None, model_overrides=None) -> str:
        """Submit a task — automatically routes to local or remote backend."""
        backend = self._get_backend(service_name)
        return await backend.submit_task(service_name, config, task_id, timeout, model_overrides)

    async def wait_for_task(self, task_id, timeout=None) -> TaskResult:
        backend = self._find_backend_for_task(task_id)
        return await backend.wait_for_task(task_id, timeout)
```

**Remote server exposes task API endpoints** (in `backend/apis/tasks.py`):
```python
@app.post("/api/v1/tasks/submit")
async def submit_task(request: TaskSubmitRequest, dal=Depends(get_dal)):
    """Accept remote task submission."""
    ...

@app.get("/api/v1/tasks/{task_id}/status")
async def get_task_status(task_id: int, dal=Depends(get_dal)):
    """Return task status for remote polling."""
    ...

@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: int, dal=Depends(get_dal)):
    """Cancel a task (local or forwarded)."""
    ...
```

**Key design principle**: The caller (task, service, API) uses `ServiceManager.submit_task()` the same way regardless of whether the service is local or remote. The `BaseTaskConfig` being Pydantic makes it naturally JSON-serializable for wire transport.

**Configuration** (in `AppConfig`):
```python
class RemoteServiceConfig(BaseModel):
    service_name: str
    base_url: str
    api_key: str = ""

class AppConfig(BaseSettings):
    ...
    remote_services: list[RemoteServiceConfig] = []
```

**Startup registration**:
```python
# In BaseAPIServer.on_startup()
for remote in config.remote_services:
    self.service_manager.register_remote_service(
        service_name=remote.service_name,
        base_url=remote.base_url,
        api_key=remote.api_key,
    )
```

### 15. Data Access Layer (DAL) — single boundary for all DB communication

**Goal**: Wrap everything that talks to the database into a single module (`src/dal/`) with a clean request/response schema API. This creates one testable boundary — unit tests only need to cover the DAL's public API to verify the entire backend's DB interaction.

**Source problem**: DB access is scattered:
- `db/db_operations.py` has CRUD functions that return ORM models
- `backend/apis/*.py` call DB operations directly and also do inline queries
- `services/*.py` sometimes call DB operations, sometimes query sessions directly
- `backend/apis/tasks.py` has `db_helper_*` functions that are called from `BaseTask` (a layering violation)
- No single place to test "all DB interactions work correctly"

**New** (`src/dal/`):
```
src/dal/
├── __init__.py          # Re-exports the DAL class or facade functions
├── base.py              # DAL base with session management
├── user_dal.py          # User domain operations
├── conversation_dal.py  # Conversation domain operations
├── task_dal.py          # Task/progress domain operations
├── file_dal.py          # File domain operations
├── exam_dal.py          # Exam domain operations
└── service_config_dal.py
```

**DAL design pattern**:
```python
# src/dal/base.py
class DALBase:
    """Base for all data access layer classes. Manages session lifecycle."""
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# src/dal/user_dal.py
from schemas.user import UserSchema, UserCreateSchema, UserUpdateSchema

class UserDAL(DALBase):
    """All user-related database operations. Returns only schemas, never ORM models."""

    def get_by_id(self, user_id: int) -> UserSchema | None:
        with self._session() as session:
            obj = session.query(UserModel).filter(UserModel.id == user_id, UserModel.state < DELETED).first()
            return UserSchema.model_validate(obj) if obj else None

    def get_by_username(self, username: str) -> UserSchema | None:
        ...

    def create(self, data: UserCreateSchema) -> UserSchema:
        with self._session() as session:
            obj = UserModel(**data.model_dump())
            session.add(obj)
            session.flush()
            return UserSchema.model_validate(obj)

    def update(self, user_id: int, data: UserUpdateSchema) -> UserSchema | None:
        ...

    def soft_delete(self, user_id: int) -> bool:
        ...

    def authenticate(self, username: str, password_hash: str) -> UserSchema | None:
        """Domain-specific: verify credentials and return user."""
        ...

# src/dal/exam_dal.py
class ExamDAL(DALBase):
    def create_exam(self, data: ExamCreateSchema) -> ExamSchema: ...
    def get_exam_with_problems(self, exam_id: int) -> ExamDetailSchema | None: ...
    def get_answer_sheets_for_exam(self, exam_id: int) -> list[AnswerSheetSchema]: ...
    def submit_answer(self, data: AnswerSubmitSchema) -> AnswerSchema: ...
    # ... all exam-related DB operations
```

**Facade for easy access**:
```python
# src/dal/__init__.py
class DataAccessLayer:
    """Single entry point for all data access. Inject this, mock this."""
    def __init__(self, session_factory):
        self.users = UserDAL(session_factory)
        self.conversations = ConversationDAL(session_factory)
        self.tasks = TaskDAL(session_factory)
        self.files = FileDAL(session_factory)
        self.exams = ExamDAL(session_factory)
        self.configs = ServiceConfigDAL(session_factory)

# Create once at startup
dal = DataAccessLayer(session_factory=SessionLocal)
```

**Usage everywhere**:
```python
# In backend API
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int, dal: DataAccessLayer = Depends(get_dal)):
    user = dal.users.get_by_id(user_id)
    if not user:
        raise HTTPException(404)
    return user

# In service/task
class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        dal = get_dal()
        exam = dal.exams.get_exam_with_problems(self.config.exam_id)
        ...

# In BaseTask (replaces the layering violation of importing from backend/apis/tasks.py)
class DBTracker:
    def _persist_state(self):
        dal = get_dal()
        dal.tasks.update_state(self.task_id, self.state.value)
    def report_progress(self, progress, message):
        dal = get_dal()
        dal.tasks.update_progress(self.task_id, progress, message)
```

**Testing — the key benefit**:
```python
# tests/conftest.py
@pytest.fixture
def dal(test_db_session):
    """Real DAL pointing at test SQLite DB."""
    return DataAccessLayer(session_factory=lambda: test_db_session)

@pytest.fixture
def mock_dal():
    """Fully mocked DAL for unit tests that don't need a real DB."""
    dal = MagicMock(spec=DataAccessLayer)
    dal.users = MagicMock(spec=UserDAL)
    dal.exams = MagicMock(spec=ExamDAL)
    ...
    return dal

# Test all DB operations via the DAL boundary
class TestUserDAL:
    def test_create_and_get(self, dal):
        user = dal.users.create(UserCreateSchema(username="test", password="hash"))
        assert user.username == "test"
        fetched = dal.users.get_by_id(user.id)
        assert fetched == user

    def test_soft_delete(self, dal):
        user = dal.users.create(UserCreateSchema(username="test", password="hash"))
        dal.users.soft_delete(user.id)
        assert dal.users.get_by_id(user.id) is None  # Filtered out

# Test backend APIs by mocking the DAL
class TestUserAPI:
    def test_get_user(self, client, mock_dal):
        mock_dal.users.get_by_id.return_value = UserSchema(id=1, username="test", ...)
        response = client.get("/api/v1/users/1")
        assert response.status_code == 200
        mock_dal.users.get_by_id.assert_called_once_with(1)

# Test services by mocking the DAL
class TestExamIngestTask:
    async def test_ingest(self, mock_dal):
        mock_dal.exams.get_exam_with_problems.return_value = ExamDetailSchema(...)
        task = ExamIngestTask(config=..., service_name=SERVICE_EXAM_INGEST)
        await task._run()
        mock_dal.exams.get_exam_with_problems.assert_called_once()
```

**This replaces** `src/db/operations/` from the earlier plan. The DAL is the new single boundary:

| Before (scattered) | After (DAL) |
|---|---|
| `db/operations/user_ops.py` | `dal/user_dal.py` |
| `backend/apis/tasks.py` → `db_helper_*` | `dal/task_dal.py` |
| Inline `session.query(...)` in services | `dal.exams.get_exam_with_problems()` |
| Tests mock DB session + operations separately | Tests mock `DataAccessLayer` once |

**Updated boundary rules**:
- `dal/` is the ONLY code that imports from `db/models/` and creates `Session` objects
- Services, tasks, and APIs import from `dal/` and `schemas/`, never from `db/` directly
- Testing the DAL = testing all DB interactions. Mocking the DAL = testing all business logic without a DB

---

## Boundary Rules

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| `config/` | stdlib only | everything else |
| `exceptions.py` | stdlib only | everything else |
| `db/constants`, `db/models/` | `config` | `schemas`, `dal`, `services`, `backend` |
| `schemas/` | `config`, `db/constants`, `exceptions` | `db/models`, `dal`, `services`, `backend` |
| `dal/` | `db/models`, `schemas`, `config`, `utilities`, `exceptions` | `services`, `backend`, `model_management` |
| `utilities/` | `config`, `exceptions` | `dal`, `services`, `backend`, `model_management` |
| `models/`, `tools/` | `config`, `utilities`, `exceptions` | `dal`, `services`, `backend`, `db` |
| `model_management/` | `models`, `config`, `utilities` | `dal`, `services`, `backend`, `db` |
| `services/` | `dal`, `schemas`, `model_management`, `models`, `utilities`, `config`, `exceptions` | `backend`, `db/` (never touches ORM or sessions) |
| `backend/` | everything | (top of dependency tree) |

**Key rules**:
- `dal/` is the ONLY code that imports from `db/models/` and manages `Session` objects
- Services, tasks, and APIs work exclusively with `dal/` and `schemas/`
- Testing the DAL = testing all DB interactions. Mocking the DAL = testing business logic without a DB

---

## Complexity Tiers (Onboarding Guide)

**Tier 1 — Day 1** (write your first task):
- `BaseTaskConfig`, `BaseTask`, `_execute() -> TaskResult`
- `get_context().dal` for DB access
- `TaskResultStatus` enum

**Tier 2 — Week 1** (production features):
- `self.progress.report()` for progress tracking
- `self.lifecycle.checkpoint()` for pause/cancel support
- `TaskConversation` for AI model calls
- `BaseAgent` for multi-step AI workflows
- Prompt templates in `src/prompts/`

**Tier 3 — Month 1** (infrastructure):
- `self.tracking.save_context()` for crash recovery
- Activity tracking and `track_span()`
- `ThrottleManager` and usage metering
- `ServiceBackend` protocol (remote execution)
- `TaskRecoveryManager` internals

## Named Constants

All magic numbers must use named constants. Key constants:
```python
# Auth
AUTH_TOKEN_EXPIRY_MINUTES = 7 * 24 * 60  # 7 days

# Task execution
DEFAULT_MAX_CONVERSATION_TURNS = 20
DEFAULT_DRAIN_TIMEOUT_SECONDS = 30.0
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30
DEFAULT_HEARTBEAT_TIMEOUT = timedelta(minutes=2)
DEFAULT_MAX_STALENESS = timedelta(hours=1)
DEFAULT_MAX_RECOVERY_ATTEMPTS = 3
DEFAULT_POLL_INTERVAL_SECONDS = 1.0

# File size enforcement
FILE_SIZE_WARN_LINES = 500
FILE_SIZE_MAX_LINES = 600

# Throttling
DEFAULT_MAX_REQUESTS_PER_MINUTE = 60
DEFAULT_MAX_AI_CALLS_PER_HOUR = 100
DEFAULT_MAX_TOKENS_PER_DAY = 1_000_000
DEFAULT_MAX_CONCURRENT_TASKS = 5
DEFAULT_THROTTLE_CACHE_TTL_SECONDS = 60
```

## Additional Design Elements (from round 3 review)

### TaskMetrics (typed, not dict)
```python
class TaskMetrics(BaseModel):
    duration_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_calls: int = 0
    retry_attempts: int = 0
```

### `track_span()` context manager (DRY — eliminates boilerplate)
```python
@contextmanager
def track_span(kind: SpanKind, name: str, **metadata):
    """Reusable span tracking — all layers use this instead of manual start/end."""
    activity = get_activity()
    if not activity:
        yield None
        return
    span_id = activity.start_span(kind, name, **metadata)
    try:
        yield span_id
    except Exception as e:
        activity.end_span(span_id, status="error", error_message=str(e))
        raise
    else:
        activity.end_span(span_id)

# Usage in any layer:
with track_span(SpanKind.AI_CALL, f"ai:{label}", model_class=model.model_class) as span_id:
    response = await model.handle_chat_completion_request_async(...)
    if span_id:
        get_activity().end_span(span_id, input_tokens=response.usage.input_tokens, ...)
```

### ContextVar propagation (explicit in BaseService)
```python
# In BaseService thread dispatch — REQUIRED for activity tracking + i18n:
import contextvars
ctx = contextvars.copy_context()
thread_pool.submit(ctx.run, task._run_wrapper)
```

### Activity middleware exclusions
```python
ACTIVITY_EXCLUDE_PATHS = {"/health", "/docs", "/openapi.json"}

class ActivityTrackingMiddleware:
    async def __call__(self, request, call_next):
        if request.url.path in ACTIVITY_EXCLUDE_PATHS:
            return await call_next(request)  # Skip tracking
        ...
```

### Async task activity pattern
For fire-and-forget task submissions, the middleware persists a "request-only" activity (Span 0). The task thread creates its own `ActivityContext` linked by `request_id`. Query both via `WHERE request_id = ?` for the full trace.

### Prompt security
Any prompt variable containing user-generated content (student answers, uploaded text) MUST be sanitized before rendering: length limits, strip control characters. Document which prompt variables accept user input in each template's header comment.

### DAL session sharing
`DALBase._session()` checks for an active transaction (via `ContextVar`) before creating a new session. If a transaction is active, it joins it. Default behavior, not opt-in:
```python
_active_session: ContextVar[Session | None] = ContextVar('dal_session', default=None)

@contextmanager
def _session(self):
    existing = _active_session.get()
    if existing:
        yield existing  # Join active transaction
        return
    # Create new session
    session = self._session_factory()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

## Implementation Order

| Step | Component | Key Files | Source Reference |
|------|-----------|-----------|-----------------|
| 1 | Project scaffold | `pyproject.toml`, `pytest.ini`, `.pre-commit-config.yaml`, `.gitignore`, `.env.example` | `D:\daily_dose_base\pyproject.toml` |
| 2 | Configuration | `src/config/settings.py` | `D:\daily_dose_of_ai\src\env_vars\__init__.py` |
| 3 | Utilities | `src/utilities/*.py` | `D:\daily_dose_base\src\utilities\` |
| 4 | DB constants + base | `src/db/constants.py`, `src/db/base.py` | `D:\daily_dose_base\src\db\database.py`, `constants.py` |
| 5 | DB models | `src/db/models/*.py` | `D:\daily_dose_of_ai\src\db\db_models.py` |
| 5b | Domain schemas | `src/schemas/*.py` | New — 1:1 with DB models, Pydantic with `from_attributes=True` |
| 5c | Exceptions | `src/exceptions.py` | New — domain exception hierarchy |
| 6 | Data Access Layer | `src/dal/*.py` — sole DB boundary, accepts/returns schemas | Replaces `D:\daily_dose_of_ai\src\db\db_operations.py` |
| 7 | Alembic | `src/alembic.ini`, `src/alembic/env.py` | `D:\daily_dose_base\src\alembic\` |
| 8 | AI tools + models | `src/tools/`, `src/models/` | `D:\daily_dose_base\src\models\`, `tools\` |
| 9 | Model management | `src/model_management/` | `D:\daily_dose_of_ai\src\model_management\` |
| 10 | Service mixins | `src/services/mixins/` | Extract from `D:\daily_dose_of_ai\src\services\base_service.py` |
| 11 | BaseTask + BaseService | `src/services/base_task.py`, `base_service.py` | `D:\daily_dose_of_ai\src\services\base_service.py` |
| 12 | Service registry | `src/services/registry.py` | New (replaces `_auto_register_services`) |
| 13 | ServiceManager | `src/service_management/service_manager.py` | `D:\daily_dose_of_ai\src\service_management\service_manager.py` |
| 14 | Concrete services | `src/services/impl/*.py` | `D:\daily_dose_of_ai\src\services\` |
| 15 | Backend schemas + deps | `src/backend/schemas/`, `dependencies.py` | `D:\daily_dose_base\src\backend\schemas\` |
| 16 | Backend APIs | `src/backend/apis/` | `D:\daily_dose_base\src\backend\apis\` |
| 17 | Servers | `src/backend/base_server.py`, `edu_server.py` | `D:\daily_dose_of_ai\src\backend\base_server.py`, `edu_server.py` |
| 18 | Test infrastructure | `tests/conftest.py` + test files | `D:\daily_dose_base\tests\` |

---

### 18. Additional design improvements from critical review

#### 18a. `convert.py` becomes unnecessary — remove it

With the DAL returning schemas (refactoring #7/#15), the need for `pyd_from_obj()` and `obj_from_pyd()` conversions disappears. Pydantic's built-in `model_validate(orm_obj)` with `from_attributes=True` handles ORM → schema inside the DAL. Outside the DAL, everything is already Pydantic. Remove `convert.py` entirely — it's a symptom of the missing schema boundary.

#### 18b. `service_names.py` should use `StrEnum`, not bare strings

Source uses `SERVICE_CRAWLER = "crawler"` as plain string constants. This means typos are silently wrong. Use `StrEnum`:
```python
class ServiceName(StrEnum):
    FILE_VALIDATE = "file_validate"
    PARSE = "parse"
    EXAM_INGEST = "exam_ingest"
    EXAM_EXTRACT = "exam_extract"
    ...
```
This gives type checking, autocomplete, and `ServiceName("typo")` raises `ValueError`.

#### 18c. `BaseAPIServer` should not manage service lifecycle directly

In the source, `BaseAPIServer` directly calls `ServiceManager`, manages lock files, and runs config reload loops. This couples the HTTP layer to service orchestration.

New rule: `BaseAPIServer` delegates lifecycle to `AppContext`. The server only calls `init_context()` on startup and `ctx.shutdown()` on teardown. All service lifecycle, recovery, and config reload is managed by `AppContext` or `ServiceManager` — not the HTTP server class.

```python
class BaseAPIServer:
    async def on_startup(self):
        config = get_config()
        self.ctx = init_context(config)
        await self.ctx.startup()   # DAL init, services start, recovery runs

    async def on_shutdown(self):
        await self.ctx.shutdown()  # Services stop, connections close
```

#### 18d. Backend API schemas vs domain schemas — clear naming convention

The plan has both `src/schemas/` (domain) and `src/backend/schemas/` (HTTP API). This could be confusing. Enforce naming:
- `src/schemas/user.py` → `UserSchema`, `UserCreateSchema` — domain objects
- `src/backend/schemas/authentication.py` → `LoginRequest`, `LoginResponse`, `TokenResponse` — HTTP shapes

Rule: domain schemas are nouns (`UserSchema`). Backend schemas are verb+noun (`LoginRequest`, `RegisterResponse`). Backend schemas may compose domain schemas but add HTTP-specific fields (pagination, links, error details).

#### 18e. Task timeout should be enforced by the base class, not just tracked

Source has `task_timed_out()` as a check the task or service calls. But if a task never checks, it runs forever. New: `_run_wrapper()` starts a watchdog timer. If `_execute()` doesn't return within timeout, the watchdog sets `_pause_requested` or raises `TaskTimedOut` via `checkpoint()`. This ensures timeout enforcement even for tasks that forget to call `checkpoint()` regularly.

```python
def _run_wrapper(self):
    ...
    if self.task_timeout_seconds:
        self._timeout_timer = threading.Timer(
            self.task_timeout_seconds,
            self._on_timeout,
        )
        self._timeout_timer.start()
    try:
        result = loop.run_until_complete(self._execute())
    finally:
        if self._timeout_timer:
            self._timeout_timer.cancel()
```

#### 18f. TaskResult.data should be typed per-task, not `dict | None`

Using `dict | None` for result data loses type safety. Each task should define its own result data schema:
```python
class ExamIngestResultData(BaseModel):
    problem_count: int
    exam_id: int
    skipped_problems: list[str] = []

class ExamIngestTask(BaseTask[ExamIngestTaskConfig]):
    async def _execute(self) -> TaskResult:
        ...
        return TaskResult(
            status=TaskResultStatus.SUCCESS,
            message=t("task.progress.extracted", count=len(problems)),
            data=ExamIngestResultData(problem_count=len(problems), exam_id=self.config.exam_id),
        )
```

Update `TaskResult`:
```python
@dataclass
class TaskResult:
    status: TaskResultStatus
    message: str = ""
    data: BaseModel | None = None      # Typed result data (serializable)
    error: Exception | None = None
    metrics: dict | None = None
```

#### 18g. Graceful shutdown must drain running tasks

Source calls `stop()` on services which tries to mark tasks as paused, but there's no drain period. New: `AppContext.shutdown()` has a configurable drain period:
```python
async def shutdown(self, drain_timeout: float = 30.0):
    """Graceful shutdown: stop accepting new tasks, wait for running ones to finish."""
    self.service_manager.stop_accepting_tasks()

    # Wait up to drain_timeout for running tasks to complete
    deadline = time.time() + drain_timeout
    while self.service_manager.has_running_tasks() and time.time() < deadline:
        await asyncio.sleep(0.5)

    # Force-pause any still-running tasks (they'll be recovered on next startup)
    self.service_manager.pause_all_running_tasks()
    self.service_manager.stop_all_services()
    self.dal.close()
```

#### 18h. Externalized, versioned prompts + Agent abstraction for AI calls

**Source problem**: Tasks embed multi-hundred-line prompt strings directly in Python code:
```python
# Example from source — actual task code is 30% prompt text
system_prompt = """You are an expert exam analyzer. Given a student's answer sheet...
[200+ lines of instructions, examples, output format specifications]
"""
response = await conversation.run_chat_completion(user_prompt=f"Analyze: {content}")
```

Problems:
- Code is 70% prompt text, 30% logic — unreadable
- Prompt changes require code changes (PR, review, deploy)
- No prompt versioning — can't A/B test or roll back
- No prompt reuse — similar prompts duplicated across tasks
- Prompt variables are embedded via f-strings — error-prone, no validation

**New design — two layers**:

##### Layer 1: Prompt templates externalized to files

**Directory**: `src/prompts/`
```
src/prompts/
├── __init__.py              # PromptLoader, render_prompt()
├── exam/
│   ├── extract_problems.md  # System prompt for problem extraction
│   ├── analyze_answer.md    # System prompt for answer analysis
│   ├── grade_answer.md      # System prompt for grading
│   └── generate_hints.md    # System prompt for hint generation
├── content/
│   ├── summarize.md
│   └── translate.md
└── shared/
    ├── output_json.md       # Reusable: "Return your response as JSON..."
    └── chain_of_thought.md  # Reusable: "Think step by step..."
```

Prompt files use Jinja2 templates:
```markdown
{# src/prompts/exam/analyze_answer.md #}
You are an expert exam grader analyzing a student's answer.

## Context
- Exam: {{ exam_name }}
- Subject: {{ subject }}
- Problem: {{ problem_text }}
- Correct answer: {{ correct_answer }}
- Student's answer: {{ student_answer }}

## Instructions
{% if analysis_depth == "detailed" %}
Provide a detailed analysis including:
1. Whether the answer is correct
2. Partial credit assessment
3. Common misconceptions identified
{% else %}
Provide a brief correct/incorrect assessment.
{% endif %}

{% include "shared/output_json.md" %}
```

**PromptLoader**:
```python
# src/prompts/__init__.py
from jinja2 import Environment, FileSystemLoader, select_autoescape

_env: Environment | None = None

def init_prompts(prompts_dir: Path | None = None):
    global _env
    prompts_dir = prompts_dir or Path(__file__).parent
    _env = Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        autoescape=select_autoescape([]),
        undefined=StrictUndefined,  # Fail on missing variables
    )

def render_prompt(template_name: str, **kwargs) -> str:
    """Render a prompt template with variables."""
    if _env is None:
        raise RuntimeError("Prompts not initialized — call init_prompts()")
    template = _env.get_template(template_name)
    return template.render(**kwargs)
```

##### Layer 2: Agent classes wrap AI call logic

Each distinct AI interaction becomes an **Agent** class — a thin wrapper that bundles: the prompt template, tools, model scenario, output parsing, and retry policy. Tasks delegate to agents instead of making raw model calls.

**Directory**: `src/agents/`
```
src/agents/
├── __init__.py
├── base_agent.py           # BaseAgent class
├── exam/
│   ├── __init__.py
│   ├── extract_problems_agent.py
│   ├── analyze_answer_agent.py
│   ├── grade_answer_agent.py
│   └── generate_hints_agent.py
└── content/
    ├── __init__.py
    └── summarize_agent.py
```

**BaseAgent with full lifecycle integration**:

The key insight: an agent execution is a **stage within a task**. The agent's conversation state is saved as part of the task's context, so if the task is paused/crashed/recovered, the agent can resume from where it left off. The agent owns its own state key in the task's context dict.

```python
# src/agents/base_agent.py
from models.task_conversation import TaskConversation, ConversationState
from prompts import render_prompt

ResultT = TypeVar("ResultT", bound=BaseModel)

class AgentStatus(str, Enum):
    """Agent execution states — no raw strings."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AgentState:
    """Serializable agent state for persistence/recovery."""
    agent_name: str
    conversation_state: dict | None = None   # ConversationState as dict
    result: dict | None = None               # Parsed result as dict (if completed)
    status: AgentStatus = AgentStatus.PENDING
    attempt: int = 0                         # Current attempt number (for retry)

class BaseAgent(Generic[ResultT]):
    """
    Wraps an AI interaction: prompt + tools + parsing + retry.

    Lifecycle-aware: agent state is saved to the parent task's context.
    If the task is recovered, the agent can resume or return cached result.
    """

    # Subclasses set these
    prompt_template: str = ""           # e.g., "exam/analyze_answer.md"
    model_scenario: str = ""            # e.g., CONTENT_EXTRACTION
    tools: list[AIToolBase] = []        # Tools available to the model
    result_type: type[ResultT] = None   # Pydantic model for parsing output
    max_turns: int = 20
    retry_policy: RetryPolicy = RETRY_AI_CALL

    def __init__(self, task: BaseTask, agent_name: str | None = None):
        self.task = task
        self.agent_name = agent_name or self.__class__.__name__
        self._tc: TaskConversation | None = None  # Active conversation
        self._state = AgentState(agent_name=self.agent_name)

    # --- State management ---

    def _context_key(self) -> str:
        """Key for this agent's state in the task's context dict."""
        return f"agent:{self.agent_name}"

    def _save_state(self):
        """Save agent state into the parent task's context."""
        if self._tc:
            self._state.conversation_state = self._tc.snapshot().model_dump()
        # Merge into task's existing context
        ctx = self.task._cached_context or {}
        ctx[self._context_key()] = asdict(self._state)
        self.task.save_context(ctx, task_stage=self.task._cached_stage)

    def _load_state(self) -> AgentState | None:
        """Load agent state from the parent task's saved context."""
        ctx = self.task._cached_context or {}
        data = ctx.get(self._context_key())
        if data:
            return AgentState(**data)
        return None

    # --- Execution ---

    def _render_system_prompt(self, **kwargs) -> str:
        """Render the system prompt template with variables."""
        return render_prompt(self.prompt_template, **kwargs)

    async def run(self, user_prompt: str, prompt_vars: dict | None = None) -> ResultT:
        """
        Execute the agent with full lifecycle support.

        Flow:
        1. Check if agent already completed (from recovered context) → return cached result
        2. Check if agent was mid-conversation (from recovered context) → resume conversation
        3. Otherwise, start fresh conversation
        4. On pause/cancel → conversation state saved automatically via TaskConversation.checkpoint()
        5. On completion → result + conversation state saved to task context
        """
        # 1. Check for previously completed result
        saved_state = self._load_state()
        if saved_state and saved_state.status == AgentStatus.COMPLETED and saved_state.result:
            logger.info(f"[{self.agent_name}] Returning cached result from recovered state")
            if self.result_type:
                return self.result_type.model_validate(saved_state.result)
            return saved_state.result

        # 2. Check for mid-conversation state to resume
        if saved_state and saved_state.conversation_state and saved_state.status == AgentStatus.RUNNING:
            logger.info(f"[{self.agent_name}] Resuming from saved conversation state")
            self._state = saved_state
            conv_state = ConversationState(**saved_state.conversation_state)
            self._tc = TaskConversation.from_snapshot(
                task=self.task,
                state=conv_state,
                tools=self.tools,
            )
            # Continue the conversation
            raw_result = await self._tc.run(user_prompt=None)  # Resume — no new prompt
        else:
            # 3. Fresh start
            self._state.status = AgentStatus.RUNNING
            self._state.attempt += 1
            self._save_state()

            system_prompt = self._render_system_prompt(**(prompt_vars or {}))
            model = self.task.get_model_for_scenario(self.model_scenario)
            conversation = model.create_conversation(
                system_prompt=system_prompt,
                tools=self.tools or None,
            )
            self._tc = TaskConversation(
                task=self.task,
                conversation=conversation,
                label=self.agent_name,
                max_turns=self.max_turns,
                retry_policy=self.retry_policy,
            )
            raw_result = await self._tc.run(user_prompt=user_prompt)

        # 4. Parse and cache result
        if self.result_type:
            result = self._parse_result(raw_result)
            self._state.result = result.model_dump()
        else:
            result = raw_result
            self._state.result = {"raw": raw_result}

        self._state.status = AgentStatus.COMPLETED
        self._save_state()

        return result

    def _parse_result(self, raw: str) -> ResultT:
        """Parse model output into typed result. Override for custom parsing."""
        import json
        data = json.loads(raw)
        return self.result_type.model_validate(data)
```

**How lifecycle events flow through the stack**:

```
Task._execute()
  └── agent.run()
        └── TaskConversation.run()
              └── model.handle_chat_completion_request_async()  ← actual AI call
                    ↕ (between tool-calling turns)
              └── task.lifecycle.checkpoint()  ← checks for pause/cancel
                    ↕ (if paused)
              └── TaskConversation saves state → agent._save_state() → task.save_context()

On recovery:
Task._execute()
  └── agent.run()  ← checks context for saved agent state
        ├── If completed → returns cached result (skip AI call entirely)
        └── If running → reconstructs conversation from snapshot, resumes
```

**Multi-agent task example — each agent stage is independently recoverable**:
```python
class ExamFullAnalysisTask(BaseTask[ExamFullAnalysisTaskConfig]):
    async def _execute(self) -> TaskResult:
        dal = get_context().dal
        answer_sheet = dal.exams.get_answer_sheet(self.config.answer_sheet_id)

        # Agent 1: Extract answers (if recovered and already done, returns cached)
        extract_agent = ExtractAnswersAgent(task=self, agent_name="extract")
        extraction = await extract_agent.run(
            user_prompt=f"Extract answers from: {answer_sheet.content}",
            prompt_vars={"exam_name": answer_sheet.exam_name},
        )
        self.progress.report(33, t("task.progress.extracted_answers"))
        await self.lifecycle.checkpoint()

        # Agent 2: Grade answers
        grade_agent = GradeAnswerAgent(task=self, agent_name="grade")
        grading = await grade_agent.run(
            user_prompt=f"Grade these answers: {extraction.model_dump_json()}",
            prompt_vars={"rubric": answer_sheet.rubric},
        )
        self.progress.report(66, t("task.progress.graded"))
        await self.lifecycle.checkpoint()

        # Agent 3: Generate feedback
        feedback_agent = GenerateFeedbackAgent(task=self, agent_name="feedback")
        feedback = await feedback_agent.run(
            user_prompt=f"Generate feedback: {grading.model_dump_json()}",
        )
        self.progress.report(100, t("task.progress.complete"))

        return TaskResult(
            status=TaskResultStatus.SUCCESS,
            data=feedback,
        )
```

If the server crashes after Agent 1 completes but during Agent 2:
1. Recovery reconstructs the task, passes saved `context` and `stage`
2. Agent 1 (`extract`) finds `status=completed` in context → returns cached result instantly
3. Agent 2 (`grade`) finds `status=running` with saved conversation → resumes from last turn
4. Agent 3 (`feedback`) starts fresh

**Zero code change needed in concrete tasks** — all recovery/resume logic is in `BaseAgent.run()`.

**Concrete agent example**:
```python
# src/agents/exam/analyze_answer_agent.py

class AnswerAnalysisResult(BaseModel):
    is_correct: bool
    score: float                  # 0.0 - 1.0
    feedback: str
    misconceptions: list[str] = []

class AnalyzeAnswerAgent(BaseAgent[AnswerAnalysisResult]):
    prompt_template = "exam/analyze_answer.md"
    model_scenario = CONTENT_EXTRACTION
    result_type = AnswerAnalysisResult
    max_turns = 5
```

**Usage in tasks — clean and readable**:
```python
class ExamAnswerAnalysisTask(BaseTask[ExamAnswerAnalysisTaskConfig]):
    async def _execute(self) -> TaskResult:
        dal = get_context().dal
        answer_sheet = dal.exams.get_answer_sheet(self.config.answer_sheet_id)

        # One line to invoke the AI — no prompt strings in task code
        agent = AnalyzeAnswerAgent(task=self)
        result = await agent.run(
            user_prompt=f"Student answer: {answer_sheet.content}",
            prompt_vars={
                "exam_name": answer_sheet.exam_name,
                "subject": answer_sheet.subject,
                "problem_text": answer_sheet.problem_text,
                "correct_answer": answer_sheet.correct_answer,
                "student_answer": answer_sheet.student_answer,
                "analysis_depth": "detailed",
            },
        )

        # result is typed: result.is_correct, result.score, result.feedback
        dal.exams.save_analysis(answer_sheet.id, result.model_dump())

        return TaskResult(
            status=TaskResultStatus.SUCCESS,
            data=result,
        )
```

**Benefits**:
1. **Task code is readable** — no 200-line prompt strings, just `agent.run()`
2. **Prompts are editable** — change `.md` files without touching Python code
3. **Prompts are reusable** — `{% include "shared/output_json.md" %}` for common patterns
4. **Prompts are testable** — render templates with test data, verify output
5. **Results are typed** — `AnswerAnalysisResult` is Pydantic, parsed and validated automatically
6. **Agent is integrated** — uses `TaskConversation` for progress, cancel, retry, token tracking
7. **Versioning path** — prompts can be loaded from DB in the future for A/B testing (override `_render_system_prompt()` to check DB first, fall back to file)

---

## Design Rule Enforcement

To ensure future edits strictly follow the architecture without breaking project cleanness, rules are enforced at **4 levels**:

### File Size Rule — No Exploding Files

A central rule: **no single file should grow large enough to become hard to read**. This was a key problem in the source (`db_operations.py` at 4164 lines, `base_service.py` at 2008 lines, `edu_server.py` at 2000+ lines).

**Guidelines**:
- **Target**: ~200-400 lines per file. Investigate splitting at ~500 lines. Hard limit: never exceed 600 lines.
- **Split by logical cohesion**: one class per file, or one tightly-related group of functions per file.
- **Directory = namespace**: If a module has 3+ files, it becomes a package (directory with `__init__.py`).
- **Re-exports**: `__init__.py` re-exports key names so consumers don't need to know the internal file structure.

**Already applied in this plan**:
- `db_operations.py` (4164 lines) → split into `dal/user_dal.py`, `dal/exam_dal.py`, etc. (~100-200 lines each)
- `base_service.py` (2008 lines) → split into `base_task.py`, `base_service.py`, `task_state.py`, `recovery.py`, plus `components/` directory (~100-200 lines each)
- `db_models.py` (724 lines) → split into `db/models/user.py`, `db/models/exam.py`, etc. (~50-150 lines each)
- `edu_server.py` (2000+ lines) → split into `backend/apis/*.py` with server just registering routes

**Enforcement**:
- Pre-commit hook checks: `wc -l` on changed Python files. Warn at 500 lines, error at 600.
- Add to `scripts/check_imports.py`:
  ```python
  # Check file sizes
  MAX_LINES = 600
  WARN_LINES = 500
  for py_file in src_dir.rglob("*.py"):
      line_count = len(py_file.read_text().splitlines())
      if line_count > MAX_LINES:
          errors.append(f"{py_file}: {line_count} lines exceeds {MAX_LINES} limit")
      elif line_count > WARN_LINES:
          warnings.append(f"{py_file}: {line_count} lines approaching limit")
  ```

### Level 1: CLAUDE.md — AI-enforced rules

`CLAUDE.md` at project root is always loaded by Claude Code. It contains the authoritative design rules that any AI-assisted editing must follow. This is the primary enforcement mechanism for AI-assisted development.

**Key sections in CLAUDE.md**:
```markdown
## Architecture Rules (MUST FOLLOW)

### Import Boundary Rules
- `dal/` is the ONLY code that imports from `db/models/` or creates Session objects
- `services/` imports from `dal/` and `schemas/`, NEVER from `db/` directly
- `backend/` is the top of the dependency tree — nothing imports from `backend/`
- `config/`, `exceptions.py`, `i18n/` are leaf modules — no app imports allowed

### Task Implementation Rules
- Concrete tasks ONLY implement `_execute() -> TaskResult`
- NEVER call complete(), fail(), cancel() directly — return TaskResult instead
- ALWAYS call `await self.lifecycle.checkpoint()` between stages
- ALWAYS use `TaskConversation` for AI model calls within tasks
- ALWAYS use `self.run_with_retry()` for external API calls

### Schema/Model Rules
- ORM models (`db/models/`) NEVER escape the `db/` and `dal/` packages
- All public APIs (DAL, services, backend) use Pydantic schemas from `schemas/`
- Every user-facing string uses `t("key")` for localization

### Service Rules
- New services MUST use `@register_service` decorator
- Services that support recovery MUST implement `reconstruct_task()`
- Task configs MUST extend `BaseTaskConfig`
```

### Level 2: Import linting — automated boundary checks

**File**: `scripts/check_imports.py`

A pre-commit hook script that statically checks import boundaries:

```python
"""
Enforce architectural import boundaries.
Run as: python scripts/check_imports.py
Exit code 0 = clean, 1 = violations found.
"""

RULES = {
    # (source_package, forbidden_import_package, reason)
    ("services", "db.models", "Services must use dal/, not db/models/ directly"),
    ("services", "backend", "Services must not import from backend/"),
    ("backend.apis", "db.models", "APIs must use dal/, not db/models/ directly"),
    ("dal", "services", "DAL must not import from services/"),
    ("dal", "backend", "DAL must not import from backend/"),
    ("config", "db", "Config must not import from db/"),
    ("config", "dal", "Config must not import from dal/"),
    ("schemas", "dal", "Schemas must not import from dal/"),
    ("schemas", "services", "Schemas must not import from services/"),
    ("models", "dal", "AI models must not import from dal/"),
    ("models", "services", "AI models must not import from services/"),
    ("i18n", "dal", "i18n must not import from dal/"),
    ("i18n", "services", "i18n must not import from services/"),
}
```

This is added to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: check-imports
      name: Check architectural import boundaries
      entry: python scripts/check_imports.py
      language: system
      types: [python]
```

### Level 3: Type checking — enforced schemas

Using `pyright` or `mypy` with strict mode ensures:
- DAL methods return `UserSchema`, not `UserModel` — type checker catches leaks
- `_execute()` returns `TaskResult`, not `str` — enforced by type signature
- `BaseTaskConfig` subclass fields are typed — Pydantic validates at runtime + type checker validates at dev time

**pyproject.toml**:
```toml
[tool.pyright]
pythonVersion = "3.10"
typeCheckingMode = "basic"
reportMissingImports = true
reportMissingTypeStubs = false

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

### Level 4: Architecture tests — runtime boundary verification

**File**: `tests/test_architecture.py`

Tests that verify the architecture at test time by scanning imports:

```python
import ast
import importlib
from pathlib import Path

def test_services_do_not_import_db_models():
    """Services must never import from db.models directly."""
    services_dir = Path("src/services")
    for py_file in services_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, 'module', '') or ''
                assert not module.startswith('db.models'), (
                    f"{py_file}: imports from db.models — use dal/ instead"
                )

def test_dal_returns_schemas_not_orm():
    """DAL method return types must be schemas, not ORM models."""
    import dal
    import inspect
    for name, cls in inspect.getmembers(dal, inspect.isclass):
        for method_name, method in inspect.getmembers(cls, inspect.isfunction):
            if method_name.startswith('_'):
                continue
            hints = get_type_hints(method)
            return_type = hints.get('return', None)
            if return_type:
                assert 'Model' not in str(return_type), (
                    f"dal.{name}.{method_name} returns ORM model — must return schema"
                )

def test_tasks_extend_base_task_config():
    """All task config classes must extend BaseTaskConfig."""
    from services.base_task import BaseTaskConfig
    import services.impl
    # Scan all task classes and verify their config types
    ...

def test_no_bare_except():
    """No bare except: statements allowed."""
    src_dir = Path("src")
    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                assert False, f"{py_file}:{node.lineno}: bare except: not allowed"
```

### Summary of enforcement layers

| Layer | What it catches | When it runs |
|-------|----------------|-------------|
| **CLAUDE.md** | AI-generated violations | Every AI edit session |
| **Import linter** | Import boundary violations | Pre-commit hook (every commit) |
| **Type checker** | Schema/model leaks, wrong return types | IDE continuous + CI |
| **Architecture tests** | Runtime boundary violations, bare excepts | `pytest` (CI + local) |

This 4-layer approach ensures rules are enforced for both human and AI developers, at both dev time and CI time.

### 19. Activity tracking, token metering, and throttling — unified observability

**Source problem**: `ExecutionProfile` only tracks timing. No token usage tracking. No user attribution. No throttling. No audit trail from API request → task → AI call → response.

**Core concept**: An **ActivityContext** flows through the entire call stack — from API entry to final response. Every component writes to it. At the end, it's persisted as an audit record. This uses `contextvars.ContextVar` (not inheritance) so it works across async/threaded boundaries without passing arguments.

#### Architecture

**Directory**: `src/activity/`
```
src/activity/
├── __init__.py             # get_activity(), start_activity(), end_activity()
├── context.py              # ActivityContext, ActivitySpan, SpanKind enum
├── metering.py             # TokenMeter, UsageSummary
├── throttle.py             # ThrottlePolicy, ThrottleManager
└── middleware.py            # FastAPI middleware for auto-tracking
```

#### Core: ActivityContext — the unified trace

```python
# src/activity/context.py
from contextvars import ContextVar
from enum import StrEnum

class SpanKind(StrEnum):
    """What type of operation this span represents."""
    API_REQUEST = "api_request"       # Incoming HTTP request
    TASK_EXECUTION = "task_execution" # Task running
    AI_CALL = "ai_call"              # LLM API call
    TOOL_CALL = "tool_call"          # AI tool execution
    DB_OPERATION = "db_operation"     # Database query/write
    EXTERNAL_API = "external_api"    # S3, voice, etc.

class ActivitySpan(BaseModel):
    """A single operation within an activity. Tracks timing + usage."""
    span_id: int                      # Auto-increment within activity
    kind: SpanKind
    name: str                         # e.g., "POST /api/v1/exams/analyze"
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: float | None = None
    parent_span_id: int | None = None # For nesting (task → subtask → AI call)

    # Token usage (only for AI_CALL spans)
    input_tokens: int = 0
    output_tokens: int = 0
    model_class: str = ""             # e.g., "openai:gpt-4o"

    # Metadata (extensible — any action can add its own fields)
    metadata: dict = {}               # e.g., {"exam_id": 123, "file_size": 1024}

    # Result
    status: str = "ok"                # "ok", "error", "throttled", "cancelled"
    error_message: str = ""

class ActivityContext(BaseModel):
    """
    Tracks a complete user interaction from API entry to final response.

    This is the "turn" — everything that happens between the user's request
    hitting our API and the response going back. All spans (API, task, AI calls,
    DB ops) are children of this context.
    """
    activity_id: int | None = None    # DB record ID (set on persist)
    user_id: int
    request_id: str                   # UUID for correlating logs
    api_endpoint: str                 # e.g., "POST /api/v1/exams/{exam_id}/analyze"
    started_at: datetime
    ended_at: datetime | None = None

    # Accumulated usage across all spans
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_calls: int = 0
    total_duration_ms: float = 0

    # All spans in this activity (flat list, parent_span_id for nesting)
    spans: dict[int, ActivitySpan] = {}  # Thread-safe: protected by lock
    _next_span_id: int = 0
    _current_span_id: int | None = None  # Active span for auto-nesting

    def start_span(self, kind: SpanKind, name: str, **metadata) -> int:
        """Start a new span. Returns span_id. Auto-nests under current span."""
        span_id = self._next_span_id
        self._next_span_id += 1
        span = ActivitySpan(
            span_id=span_id,
            kind=kind,
            name=name,
            started_at=get_utcnow(),
            parent_span_id=self._current_span_id,
            metadata=metadata,
        )
        self.spans[span_id] = span
        self._current_span_id = span_id
        return span_id

    def end_span(self, span_id: int, status: str = "ok",
                 input_tokens: int = 0, output_tokens: int = 0,
                 error_message: str = "", **extra_metadata):
        """End a span. Accumulates token usage into activity totals."""
        span = self.spans[span_id]
        span.ended_at = get_utcnow()
        span.duration_ms = (span.ended_at - span.started_at).total_seconds() * 1000
        span.status = status
        span.error_message = error_message
        span.input_tokens = input_tokens
        span.output_tokens = output_tokens
        span.metadata.update(extra_metadata)

        # Accumulate into activity totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        if span.kind == SpanKind.AI_CALL:
            self.total_ai_calls += 1

        # Pop current span back to parent
        self._current_span_id = span.parent_span_id

# --- Context variable (flows through async + threaded code) ---
_activity_var: ContextVar[ActivityContext | None] = ContextVar('activity', default=None)

def get_activity() -> ActivityContext | None:
    """Get the current activity context. None if not in a tracked request."""
    return _activity_var.get()

def set_activity(ctx: ActivityContext):
    _activity_var.set(ctx)

def clear_activity():
    _activity_var.set(None)
```

#### How each layer writes to it

**FastAPI middleware** — creates/closes the activity:
```python
# src/activity/middleware.py
class ActivityTrackingMiddleware:
    async def __call__(self, request: Request, call_next):
        user = get_current_user_or_none(request)
        ctx = ActivityContext(
            user_id=user.id if user else -1,
            request_id=str(uuid.uuid4()),
            api_endpoint=f"{request.method} {request.url.path}",
            started_at=get_utcnow(),
        )
        set_activity(ctx)

        span_id = ctx.start_span(SpanKind.API_REQUEST, ctx.api_endpoint)
        try:
            response = await call_next(request)
            ctx.end_span(span_id, status="ok")
            return response
        except Exception as e:
            ctx.end_span(span_id, status="error", error_message=str(e))
            raise
        finally:
            ctx.ended_at = get_utcnow()
            ctx.total_duration_ms = (ctx.ended_at - ctx.started_at).total_seconds() * 1000
            # Persist the activity record
            dal = get_context().dal
            dal.activities.create(ctx)
            clear_activity()
```

**BaseTask** — auto-creates a task span:
```python
class BaseTask:
    def _run_wrapper(self):
        activity = get_activity()
        span_id = None
        if activity:
            span_id = activity.start_span(
                SpanKind.TASK_EXECUTION,
                f"task:{self.service_name}",
                task_id=self.task_id,
                config_type=type(self.config).__name__,
            )
        try:
            ... # run _execute()
        finally:
            if activity and span_id is not None:
                activity.end_span(span_id, status=self.result.status.value if self.result else "error")
```

**TaskConversation** — tracks each AI call:
```python
class TaskConversation:
    async def run(self, user_prompt=None) -> str:
        ...
        activity = get_activity()
        span_id = activity.start_span(
            SpanKind.AI_CALL,
            f"ai:{self.label}",
            model_class=self.conversation.model.model_class,
        ) if activity else None

        response = await retry_async(
            self.conversation.model.handle_chat_completion_request_async, ...
        )

        if activity and span_id is not None:
            activity.end_span(
                span_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model_class=self.conversation.model.model_class,
            )
        ...
```

**DAL** (optional, for audit-level tracking):
```python
class DALBase:
    @contextmanager
    def _session(self):
        activity = get_activity()
        span_id = activity.start_span(SpanKind.DB_OPERATION, self.__class__.__name__) if activity else None
        try:
            ...
            if activity and span_id is not None:
                activity.end_span(span_id)
        except Exception as e:
            if activity and span_id is not None:
                activity.end_span(span_id, status="error", error_message=str(e))
            raise
```

#### Token metering and usage summaries

```python
# src/activity/metering.py
class UsageSummary(BaseModel):
    """Aggregated usage for a user over a time period."""
    user_id: int
    period_start: datetime
    period_end: datetime
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_calls: int = 0
    total_api_requests: int = 0
    total_tasks: int = 0
    breakdown_by_model: dict[str, TokenUsage] = {}  # model_class -> usage
    breakdown_by_endpoint: dict[str, int] = {}       # endpoint -> call count

class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0

# DAL method for aggregation
class ActivityDAL(DALBase):
    def get_usage_summary(self, user_id: int, since: datetime) -> UsageSummary:
        """Aggregate usage from activity records."""
        ...

    def get_recent_activities(self, user_id: int, limit: int = 50) -> list[ActivitySchema]:
        """Get recent activities for audit UI."""
        ...
```

#### Throttling framework

```python
# src/activity/throttle.py
class ThrottlePolicy(BaseModel):
    """Configurable rate/usage limits."""
    max_requests_per_minute: int = 60
    max_ai_calls_per_hour: int = 100
    max_tokens_per_day: int = 1_000_000
    max_concurrent_tasks: int = 5

class ThrottleResult(BaseModel):
    allowed: bool
    reason: str = ""
    retry_after_seconds: float = 0

class ThrottleManager:
    """Checks usage against policies. Uses DAL for persistence."""

    def __init__(self, dal: DataAccessLayer, default_policy: ThrottlePolicy):
        self.dal = dal
        self.default_policy = default_policy
        # In-memory sliding window for request rate (fast path)
        self._request_windows: dict[int, list[datetime]] = {}  # user_id -> timestamps

    def check(self, user_id: int, action: SpanKind = SpanKind.API_REQUEST) -> ThrottleResult:
        """Check if user is within limits. Call at API entry."""
        policy = self._get_policy_for_user(user_id)

        # Fast path: in-memory request rate check
        if action == SpanKind.API_REQUEST:
            window = self._request_windows.get(user_id, [])
            recent = [t for t in window if (get_utcnow() - t).total_seconds() < 60]
            if len(recent) >= policy.max_requests_per_minute:
                return ThrottleResult(allowed=False, reason="rate_limit", retry_after_seconds=5)
            recent.append(get_utcnow())
            self._request_windows[user_id] = recent

        # Slow path: DB-backed usage checks (cached, refreshed periodically)
        if action == SpanKind.AI_CALL:
            usage = self.dal.activities.get_usage_summary(user_id, since=get_utcnow() - timedelta(hours=1))
            if usage.total_ai_calls >= policy.max_ai_calls_per_hour:
                return ThrottleResult(allowed=False, reason="ai_call_limit")

        return ThrottleResult(allowed=True)
```

**FastAPI integration** — throttle at middleware level:
```python
class ActivityTrackingMiddleware:
    async def __call__(self, request, call_next):
        ...
        # Throttle check before processing
        throttle = get_context().throttle_manager
        result = throttle.check(user_id=ctx.user_id, action=SpanKind.API_REQUEST)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": t("throttle.rate_limited"), "retry_after": result.retry_after_seconds},
                headers={"Retry-After": str(int(result.retry_after_seconds))},
            )
        ...
```

**Before AI calls** — throttle at task level:
```python
class TaskConversation:
    async def run(self, user_prompt=None) -> str:
        # Check token/call budget before each AI call
        activity = get_activity()
        if activity:
            throttle = get_context().throttle_manager
            result = throttle.check(user_id=activity.user_id, action=SpanKind.AI_CALL)
            if not result.allowed:
                raise AIRateLimitError(t("throttle.ai_call_limit"))
        ...
```

#### DB schema for activity records

```python
# In src/db/models/activity.py
class ActivityModel(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    request_id: Mapped[str]
    api_endpoint: Mapped[str]
    started_at: Mapped[datetime]
    ended_at: Mapped[Optional[datetime]]
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_ai_calls: Mapped[int] = mapped_column(default=0)
    total_duration_ms: Mapped[float] = mapped_column(default=0)
    spans_json: Mapped[Optional[str]]  # JSON blob of all spans
    state: Mapped[int] = mapped_column(default=0)

# Index for usage queries
Index("ix_activities_user_time", ActivityModel.user_id, ActivityModel.started_at)
```

#### Why `contextvars` + spans — not base class inheritance

**Option rejected: Base class for every action**
```python
# This would require EVERY function that does anything trackable to inherit from TrackedAction
class TrackedAction:
    user_id: int
    ...
class AICall(TrackedAction): ...
class DBQuery(TrackedAction): ...
```
Problem: An AI call isn't an "object" you create and run — it's an `await model.handle_chat_completion_request_async()` call. Forcing inheritance means wrapping every library call in a class. It's invasive and doesn't compose (what if one function does both DB + AI?).

**Option chosen: `contextvars.ContextVar` + spans**
- **Zero-argument tracking** — components call `get_activity()` to find the current context, no need to pass it through every function signature
- **Auto-nesting** — `start_span()` auto-parents under the current span, building the tree automatically
- **Extensible** — adding a new `SpanKind` (e.g., `VOICE_SYNTHESIS`) requires zero changes to existing code. Just call `activity.start_span(SpanKind.VOICE_SYNTHESIS, ...)` wherever the new action happens
- **Thread-safe** — `contextvars.ContextVar` works correctly in both async and threaded contexts (it copies into new threads if you use `copy_context().run()`)
- **Optional** — if `get_activity()` returns `None`, components silently skip tracking. No overhead when tracking is disabled (e.g., in tests, background tasks not triggered by a user)

#### Unified tagging

Every span inherits the `user_id` and `request_id` from its `ActivityContext`. This means:
- An AI call 3 levels deep in a subtask tree is still tagged to the original user
- All spans in one user request share the same `request_id` for log correlation
- Usage aggregation queries `WHERE user_id = ? AND started_at > ?` give complete per-user billing data

To track non-user-triggered activities (cron jobs, background tasks), create an `ActivityContext` with `user_id=-1` (system) or a service account ID.

#### End-to-end flow examples

##### Flow 1: Happy path — User analyzes an exam answer sheet

```
USER → POST /api/v1/exams/42/analyze  (body: {answer_sheet_id: 99})
│
├─ [MIDDLEWARE] ActivityTrackingMiddleware
│   ├─ ThrottleManager.check(user_id=7, API_REQUEST) → allowed
│   ├─ ActivityContext created: {user_id: 7, request_id: "abc-123", api_endpoint: "POST /exams/42/analyze"}
│   └─ Span 0 started: {kind: API_REQUEST, name: "POST /exams/42/analyze"}
│
├─ [API ENDPOINT] api_analyze_answer_sheet()
│   ├─ dal.exams.get_answer_sheet(99) → AnswerSheetSchema
│   │   └─ Span 1: {kind: DB_OPERATION, parent: 0, name: "ExamDAL.get_answer_sheet"}
│   │
│   ├─ ServiceManager.submit_task(SERVICE_EXAM_ANALYSIS, config={answer_sheet_id: 99, user_id: 7})
│   │   ├─ Task DB record created → task_id = 456
│   │   └─ Task queued for execution
│   │
│   └─ return {task_id: 456, status: "pending"}  ← immediate response to user
│
├─ [TASK THREAD] ExamAnswerAnalysisTask._run_wrapper()
│   ├─ Span 2: {kind: TASK_EXECUTION, parent: 0, name: "task:exam_analysis", task_id: 456}
│   ├─ State: PENDING → RUNNING  (DB write)
│   │
│   ├─ _execute(context=None, stage=0):
│   │   │
│   │   ├─ [AGENT 1] ExtractAnswersAgent.run()
│   │   │   ├─ ThrottleManager.check(user_id=7, AI_CALL) → allowed
│   │   │   ├─ render_prompt("exam/extract_answers.md", exam_name="Math Final")
│   │   │   ├─ TaskConversation.run("Extract answers from: ...")
│   │   │   │   ├─ Span 3: {kind: AI_CALL, parent: 2, model: "openai:gpt-4o"}
│   │   │   │   ├─ Model returns tool_calls: [{"name": "parse_table", ...}]
│   │   │   │   │   └─ Span 4: {kind: TOOL_CALL, parent: 3, name: "parse_table"}
│   │   │   │   ├─ Model returns final response
│   │   │   │   └─ Span 3 ended: {input_tokens: 2100, output_tokens: 850, status: "ok"}
│   │   │   ├─ Agent result parsed → ExtractedAnswers(answers=[...])
│   │   │   └─ Agent state saved to context: {agent:extract → status: COMPLETED, result: {...}}
│   │   │
│   │   ├─ self.progress.report(33, "Answers extracted")  (DB write, debounced)
│   │   ├─ await self.lifecycle.checkpoint()  ← checks for cancel/pause
│   │   ├─ self.tracking.save_context({...}, stage=1)  (DB write)
│   │   │
│   │   ├─ [AGENT 2] GradeAnswerAgent.run()
│   │   │   ├─ ThrottleManager.check(user_id=7, AI_CALL) → allowed
│   │   │   ├─ Span 5: {kind: AI_CALL, parent: 2, model: "openai:gpt-4o"}
│   │   │   │   └─ Span 5 ended: {input_tokens: 1800, output_tokens: 600, status: "ok"}
│   │   │   └─ Agent state saved: {agent:grade → status: COMPLETED, result: {...}}
│   │   │
│   │   ├─ self.progress.report(66, "Graded")
│   │   ├─ await self.lifecycle.checkpoint()
│   │   ├─ self.tracking.save_context({...}, stage=2)
│   │   │
│   │   ├─ dal.exams.save_analysis(answer_sheet_id=99, result=...)
│   │   │   └─ Span 6: {kind: DB_OPERATION, parent: 2, name: "ExamDAL.save_analysis"}
│   │   │
│   │   ├─ self.progress.report(100, "Complete")
│   │   └─ return TaskResult(status=SUCCESS, data=AnalysisResultData(...))
│   │
│   ├─ State: RUNNING → COMPLETED  (DB write)
│   └─ Span 2 ended: {status: "ok"}
│
├─ Span 0 ended: {status: "ok"}
└─ ActivityContext persisted to DB:
    {
      activity_id: 789,
      user_id: 7,
      request_id: "abc-123",
      api_endpoint: "POST /exams/42/analyze",
      total_input_tokens: 3900,
      total_output_tokens: 1450,
      total_ai_calls: 2,
      total_duration_ms: 12340,
      spans: [Span 0..6]  ← full trace tree
    }
```

**DB records after happy path**:
| Table | Record |
|-------|--------|
| `activities` | `{id: 789, user_id: 7, total_input_tokens: 3900, total_output_tokens: 1450, ...}` |
| `tasks` | `{id: 456, state: "completed", service: "exam_analysis", config: {...}, stage: 2}` |
| `exam_analyses` | The actual analysis result |

---

##### Flow 2: Recovered flow — Server crashes during Agent 2, recovers on restart

```
[Same start as Flow 1 through Agent 1 completing and checkpoint at stage=1]

├─ [AGENT 2] GradeAnswerAgent.run()
│   ├─ Span 5: {kind: AI_CALL, parent: 2, model: "openai:gpt-4o"}
│   ├─ Model is mid-response...
│   │
│   ╳ ═══ SERVER CRASH ═══
│
│  DB state at crash time:
│  - Task 456: state=RUNNING, stage=1, context={agent:extract → COMPLETED, agent:grade → RUNNING, agent:grade.conv_state → {...}}
│  - Activity 789: partially persisted (middleware didn't get to persist — lost)
│  - Last heartbeat: 15 seconds ago

═══ SERVER RESTARTS ═══

├─ [STARTUP] AppContext.startup()
│   ├─ init_db(), setup_logger(), load_locales(), init_prompts()
│   ├─ ServiceManager.start_all_services()
│   │
│   └─ TaskRecoveryManager.recover_on_startup()
│       ├─ Query: tasks WHERE state IN ('running', 'paused', 'pending')
│       ├─ Found task 456: state=RUNNING, last_heartbeat=15s ago (> 2min timeout? No, only 15s)
│       │   ... wait, heartbeat_timeout is 2 minutes, 15s < 2min → skip (might still be running)
│       │
│       │   [After 2 minutes with no heartbeat update]
│       ├─ Recovery scan runs again (periodic check, or next startup)
│       ├─ Found task 456: last_heartbeat now 2+ minutes stale → ORPHANED
│       ├─ recovery_attempts: 0 < max(3) → recoverable
│       ├─ age: 3 minutes < max_staleness(1 hour) → not too stale
│       │
│       ├─ Reconstruct task:
│       │   ├─ Load config_snapshot: ExamAnswerAnalysisTaskConfig(answer_sheet_id=99)
│       │   ├─ Load context: {agent:extract → COMPLETED, agent:grade → RUNNING, conv_state: {...}}
│       │   ├─ Load stage: 1
│       │   ├─ service.reconstruct_task(task_id=456, config, context, stage=1)
│       │   └─ task.task_id = 456 (same DB record)
│       │
│       ├─ Increment recovery_attempts → 1
│       ├─ State: → PENDING (DB write)
│       └─ Re-submit to ServiceManager

├─ [TASK THREAD - RECOVERED] ExamAnswerAnalysisTask._run_wrapper()
│   ├─ NEW ActivityContext created: {user_id: 7, request_id: "recovery-456"}
│   ├─ Span 0: {kind: TASK_EXECUTION, name: "task:exam_analysis:recovery"}
│   ├─ State: PENDING → RUNNING
│   │
│   ├─ _execute(context={agent:extract→COMPLETED, agent:grade→RUNNING, ...}, stage=1):
│   │   │
│   │   ├─ stage=1 ≥ 1, so skip Agent 1
│   │   │
│   │   ├─ [AGENT 1] ExtractAnswersAgent.run()
│   │   │   ├─ _load_state() → AgentState(status=COMPLETED, result={...})
│   │   │   └─ RETURN CACHED RESULT ← no AI call! Instant.
│   │   │
│   │   ├─ [AGENT 2] GradeAnswerAgent.run()
│   │   │   ├─ _load_state() → AgentState(status=RUNNING, conv_state={...})
│   │   │   ├─ Reconstruct conversation from snapshot (messages already sent)
│   │   │   ├─ TaskConversation.run(user_prompt=None)  ← RESUME, no new prompt
│   │   │   │   ├─ Span 1: {kind: AI_CALL, parent: 0, model: "openai:gpt-4o"}
│   │   │   │   ├─ Model receives previous messages + continues
│   │   │   │   └─ Span 1 ended: {input_tokens: 1800, output_tokens: 600}
│   │   │   └─ Agent state saved: {agent:grade → COMPLETED, result: {...}}
│   │   │
│   │   ├─ checkpoint(), save_context(stage=2)
│   │   │
│   │   ├─ [AGENT 3 — same as happy path]
│   │   │
│   │   └─ return TaskResult(status=SUCCESS, ...)
│   │
│   ├─ State: RUNNING → COMPLETED
│   └─ Activity persisted: {total_input_tokens: 1800, total_ai_calls: 1}  ← only the recovery work

TOTAL across both runs:
  - Original activity (lost in crash): ~3900 input tokens, 2 AI calls
  - Recovery activity: ~1800 input tokens, 1 AI call  (Agent 1 cached, Agent 2 resumed)
  - Billing: sum of both activity records for user_id=7
```

**Key recovery behaviors**:
- Agent 1 result was cached → **zero cost on recovery**
- Agent 2 conversation state was saved → **resumes mid-conversation, not from scratch**
- Task stage was at 1 → skips already-completed work
- Same task_id (456) → DB record updated, not duplicated

---

##### Flow 3: Failed flow — AI rate limit exhausted, task fails, user sees error

```
USER → POST /api/v1/exams/42/analyze  (body: {answer_sheet_id: 99})
│
├─ [MIDDLEWARE] ActivityTrackingMiddleware
│   ├─ ThrottleManager.check(user_id=7, API_REQUEST) → allowed (under rate limit)
│   ├─ ActivityContext created
│   └─ Span 0: {kind: API_REQUEST}
│
├─ [API ENDPOINT] → submit task → task_id=457 → return {task_id: 457}
│
├─ [TASK THREAD] ExamAnswerAnalysisTask._run_wrapper()
│   ├─ Span 1: {kind: TASK_EXECUTION, parent: 0}
│   ├─ State: PENDING → RUNNING
│   │
│   ├─ _execute(context=None, stage=0):
│   │   │
│   │   ├─ [AGENT 1] ExtractAnswersAgent.run()
│   │   │   ├─ ThrottleManager.check(user_id=7, AI_CALL) → allowed
│   │   │   ├─ TaskConversation.run(...)
│   │   │   │   ├─ Span 2: {kind: AI_CALL, model: "openai:gpt-4o"}
│   │   │   │   ├─ retry_async() attempt 1 → OpenAI returns 429 (rate limit)
│   │   │   │   │   ├─ RetryPolicy.should_retry(RateLimitError, attempt=0) → True
│   │   │   │   │   ├─ delay = 2.0 * 2^0 * jitter = ~2.3s
│   │   │   │   │   ├─ self.progress.report(0, "[extract] Retry 1/3: rate limited")
│   │   │   │   │   ├─ await self.lifecycle.checkpoint()  ← still running, continue
│   │   │   │   │   └─ await asyncio.sleep(2.3)
│   │   │   │   ├─ retry_async() attempt 2 → OpenAI returns 429 again
│   │   │   │   │   ├─ delay = 2.0 * 2^1 * jitter = ~4.8s
│   │   │   │   │   └─ await asyncio.sleep(4.8)
│   │   │   │   ├─ retry_async() attempt 3 → OpenAI returns 429 again
│   │   │   │   │   ├─ delay = 2.0 * 2^2 * jitter = ~9.1s
│   │   │   │   │   └─ await asyncio.sleep(9.1)
│   │   │   │   ├─ retry_async() attempt 4 → exceeds max_retries(3)
│   │   │   │   │   └─ RAISES AIRateLimitError("OpenAI rate limit exceeded")
│   │   │   │   │
│   │   │   │   └─ Span 2 ended: {status: "error", error: "rate_limit", input_tokens: 0, output_tokens: 0}
│   │   │   │
│   │   │   ├─ Agent catches → saves state: {agent:extract → status: FAILED}
│   │   │   └─ RAISES AIRateLimitError (propagates up)
│   │   │
│   │   └─ EXCEPTION propagates out of _execute()
│   │
│   ├─ _run_wrapper catches Exception:
│   │   ├─ logger.exception("Task 457 failed with unhandled exception")
│   │   ├─ self.result = TaskResult(
│   │   │     status=FAILED,
│   │   │     message=t("task.result.failed", reason="AI rate limit exceeded after 3 retries"),
│   │   │     error=AIRateLimitError(...),
│   │   │     metrics={"retry_attempts": 3, "total_retry_delay_ms": 16200},
│   │   │   )
│   │   └─ State: RUNNING → FAILED  (DB write)
│   │
│   └─ Span 1 ended: {status: "error", error_message: "AIRateLimitError"}
│
├─ Span 0 ended: {status: "error"}
└─ ActivityContext persisted:
    {
      activity_id: 790,
      user_id: 7,
      total_input_tokens: 0,     ← no successful AI calls
      total_output_tokens: 0,
      total_ai_calls: 0,         ← failed calls don't count as completed calls
      total_duration_ms: 18500,
      spans: [
        Span 0: API_REQUEST (error),
        Span 1: TASK_EXECUTION (error),
        Span 2: AI_CALL (error, 3 retries, rate_limit)
      ]
    }

USER polls → GET /api/v1/tasks/457/status
  → {state: "failed", message: "AI rate limit exceeded after 3 retries", progress: 0}
```

**What the audit shows**:
- Activity 790: user 7 attempted exam analysis, 0 tokens consumed (not billed), failed due to rate limit
- Task 457: state=FAILED, recovery_attempts=0, could be retried manually
- Span tree: exactly where in the pipeline the failure occurred (Agent 1, AI call, 3rd retry)

**User can retry** → `POST /api/v1/tasks/457/retry`:
- `TaskRecoveryManager._recover_task(task_457)` → reconstructs, re-submits
- Since no agents completed, starts fresh (no cached results to reuse)
- New activity record created (791) — separate billing event

#### Adding the activity tracking to AppContext

```python
@dataclass
class AppContext:
    config: AppConfig
    dal: DataAccessLayer
    service_manager: ServiceManager
    model_manager: ModelManager
    throttle_manager: ThrottleManager   # NEW
```

---

## Review Findings & Resolutions

Five parallel reviews (robustness, cleanness, understandability, testability, efficiency) identified issues. Here are the resolutions:

### Structural Fixes (applied to plan)

1. **CRUDBase removed** — DAL (refactoring #15) is the sole DB access pattern. No `src/db/operations/`.
2. **Standardize dependency access** — `get_context()` for all non-FastAPI code. `get_dal()`, `get_service_manager()` exist ONLY as `Depends()` wrappers. Tasks/services always use `get_context().dal`.
3. **Consistent naming** — Abstract method is `_execute()` everywhere (not `_run()`). Task ID is `int` everywhere (not `str`).
4. **`FileNotFoundError`** renamed to `StorageFileNotFoundError` to avoid shadowing builtin.
5. **`_child_weights`** set AFTER `submit_task()` returns real task_id, not before.
6. **`AgentState.status`** uses `AgentStatus` enum (already applied).

### Design Decisions (added to plan)

7. **Composition over mixins for BaseTask** — Instead of `class BaseTask(DBTrackingMixin, ProfilingMixin, ...)`, use owned components:
   ```python
   class BaseTask(Generic[ConfigT]):
       def __init__(self, config: ConfigT, service_name: str, ...):
           self.lifecycle = LifecycleManager(self)    # state machine
           self.progress = ProgressTracker(self)       # hierarchical progress
           self.tracking = DBTracker(self)             # DB persistence
           self.profiler = Profiler(self)              # execution profiling
   ```
   Concrete tasks use `self.progress.report(30, "...")` not `self.progress.report(30, "...")`. Each component is independently testable and discoverable. No MRO confusion.

8. **DAL transaction support** — Add `dal.transaction()` for multi-step atomic operations:
   ```python
   async with dal.transaction() as tx:
       tx.exams.save_problems(exam_id, problems)
       tx.tasks.update_state(task_id, "completed")
   # Single commit; rollback on exception
   ```

9. **Recovery scans PENDING tasks too** — `RecoveryPolicy.auto_recover_states` includes `TaskState.PENDING`. PENDING tasks older than 5 minutes with no heartbeat are re-submitted.

10. **Hierarchical cancel via DB** — During recovery, query `parent_task_id` to find orphaned children. If parent is CANCELLED/FAILED, cascade to children.

11. **DB write throttling** — Persist state only on: (a) terminal transitions, (b) explicit `save_context()`, (c) `checkpoint()` calls. Progress writes debounced to max once per 2 seconds. Heartbeat interval ≥ 30 seconds.

12. **Use `contextvars.ContextVar`** instead of module-level `_context` global and `threading.local()` for i18n. Works correctly in both async and threaded contexts.

13. **Timeout enforcement via `asyncio.wait_for()`** instead of `threading.Timer`. Testable with fake clocks.

14. **Timeout propagation** — `submit_and_wait_subtask()` passes `min(parent_remaining_time, explicit_timeout)` to children.

15. **Specify heartbeat daemon** — `DBTracker` starts a background `threading.Timer` that fires every `heartbeat_interval/2` seconds to write heartbeat to DB.

### Scope Decisions (deferred to v2)

16. **Remote backend** — Keep `ServiceBackend` protocol in the design but only implement `LocalServiceBackend` for v1. Remote backend is v2.

17. **Agent abstraction** — Keep in plan but mark as opt-in. TaskConversation + prompt files is the default for v1 tasks. Agents are for tasks with multiple AI interactions that need independent recovery.

18. **Stage-based resume** — Keep but make opt-in. Simple tasks can ignore `context`/`stage` params and just run fresh each time. Recovery is for long-running multi-step tasks only.

### Understandability Improvements

19. **Minimal task example** — Add to CLAUDE.md:
    ```python
    # Simplest possible task — no recovery, no agents, no subtasks
    class GreetTask(BaseTask[BaseTaskConfig]):
        async def _execute(self) -> TaskResult:
            return TaskResult(status=TaskResultStatus.SUCCESS, message="Hello!")
    ```

20. **Make wrong usage impossible** — `complete()`, `fail()`, `cancel()` are `_private` methods. ORM models are NOT exported from `db/models/__init__.py` (only `Base` for Alembic). `task_id` is `int | None` (not sentinel -1) — methods that need it raise if None.

21. **Rename `src/backend/schemas/`** to `src/backend/contracts/` to distinguish from domain `src/schemas/`.

### Missing Tests (added)

22. Add `tests/services/test_recovery.py` — orphaned task detection, staleness, max retries, cascade
23. Add `tests/agents/test_base_agent.py` — cached result return, mid-conversation resume, fresh start
24. Add `tests/services/test_concurrent.py` — N tasks submitted simultaneously, verify no deadlock

### V2 Review Resolutions (critical fixes from second review round)

**Thread safety (from robustness + testability reviews):**

25. **`asyncio.Event` → `threading.Event`** for cross-thread pause signaling. `pause()` is called from API thread; `checkpoint()` runs in task thread. `asyncio.Event` is not thread-safe across different loops. Use `threading.Event` for `_pause_event`, bridge with `await asyncio.get_event_loop().run_in_executor(None, self._pause_event.wait)` in `checkpoint()`.

26. **`_children` list access must be locked** — `cancel()`/`pause()` iterate `_children` from caller thread while task thread appends via `submit_and_wait_subtask()`. Snapshot under lock: `with self._state_lock: children = list(self._children)`.

27. **`checkpoint()` must be fully atomic** — acquire `_state_lock` for the entire read-check-transition sequence. Don't read `_state` or `_pause_requested` outside the lock.

28. **ContextVar propagation to worker threads** — `_run_wrapper()` must run inside `contextvars.copy_context().run()`. In `BaseService` thread dispatch: `ctx = contextvars.copy_context(); thread_pool.submit(ctx.run, task._run_wrapper)`. Without this, `get_activity()` returns None in task threads and all tracking silently fails.

29. **ActivityContext span access must be thread-safe** — Use `dict[int, ActivitySpan]` for spans (not list), protect `_next_span_id` and `_current_span_id` with lock. Make `_current_span_id` a ContextVar so each thread tracks its own current span.

**Testability (from testability review):**

30. **Add `MockAIModel`** — `src/models/mock_model.py`: deterministic model returning canned responses, configurable per-test. Wire into `ModelManager` when `config.mock.use_mock_model` is True. **This is critical — without it, no task or agent can be tested in CI.**

31. **Add `BaseTask.run_async()`** — testable entry point that runs lifecycle within an existing event loop (no thread creation). `_run_wrapper()` delegates to it. Tests call `await task.run_async()` directly.

32. **Add `override_context()` context manager** — concrete test seam for `AppContext`:
    ```python
    @contextmanager
    def override_context(ctx: AppContext):
        global _context
        old = _context
        _context = ctx
        try: yield ctx
        finally: _context = old
    ```

33. **`retry_async` accepts `sleep_func` parameter** — defaults to `asyncio.sleep`. Tests inject `async def fake_sleep(d): pass` for instant, deterministic retries.

34. **Add test factories** — `tests/factories.py` with `make_agent_state()`, `make_task_context()`, `make_conversation_state()`, `make_mock_model(responses=[...])`.

**Performance (from efficiency review):**

35. **`_transition()` does NOT persist to DB** — only sets in-memory state. Persist at flush points only: `checkpoint()`, `save_context()`, terminal transitions. Cuts minimum DB writes from 5 to 2 per task.

36. **Progress propagation decoupled from DB** — recalculate in memory only. Persist root task's aggregated progress on a timer (every 2 seconds), not on every child update.

37. **Throttle caching** — `ThrottleManager` caches per-user AI call/token counts in memory with 60-second TTL. DB aggregation query runs at most once per minute per user, not per AI call.

38. **`_persist_state()` outside the lock** — set state in memory under lock, release lock, then persist. Prevents holding lock during DB round-trip. Use `RLock` for safety.

39. **Activity middleware persistence is best-effort** — wrap `dal.activities.create(ctx)` in try/except. Never let tracking failures replace the user's actual response.

40. **Periodic recovery scan** — add background asyncio task during normal server operation that runs recovery scan every `heartbeat_timeout` interval. Don't rely solely on startup scan.

**Consistency (from cleanness review):**

41. All code examples updated to use `_execute()` (not `_run()`), return `TaskResult` (not call `complete()`), use `int` for task_id (not `str`), use `self.progress.report()` / `self.lifecycle.checkpoint()` / `self.tracking.save_context()` (composition, not mixins), use `get_context().dal` (not `get_dal()` in non-FastAPI code).

42. `FileNotFoundError` → `StorageFileNotFoundError` in exception hierarchy code.

43. `task_id: int | None = None` (not sentinel -1). Methods that need it raise immediately if None.

44. `AppContext` definition includes `throttle_manager`. `init_context()` creates it.

45. `load_context()` returns `({}, 0)` not `(None, 0)` — context is always a dict, never None.

## Verification Plan

Each step must pass ALL checks before moving to the next:

### Per-step validation (run after each implementation step)
```bash
# 1. Linter & formatter (must pass — enforced by pre-commit)
pre-commit run --all-files          # black, isort, autoflake, pyupgrade

# 2. Import boundary check
python scripts/check_imports.py     # Architectural boundary enforcement

# 3. Type checking
pyright src/                        # Type errors caught at dev time

# 4. Tests
pytest -v --tb=short               # All tests pass
```

### Milestone checkpoints

1. **After Step 1-2** (scaffold + config):
   - `pre-commit run --all-files` passes
   - `python -c "from config import get_config; print(get_config())"` — config loads from .env

2. **After Step 4-6** (DB + schemas + DAL):
   - `pytest tests/dal/` — DAL creates tables in SQLite, CRUD returns correct schemas
   - `python scripts/check_imports.py` — no boundary violations
   - `pyright src/db/ src/dal/ src/schemas/` — type-clean

3. **After Step 8-9** (AI models + model management):
   - `pytest tests/model_management/` — ModelManager scenario routing works
   - `pyright src/models/ src/model_management/` — type-clean

4. **After Step 10-13** (services + task infra):
   - `pytest tests/services/` — registry, BaseTask lifecycle, components, ServiceManager
   - `pytest tests/services/test_recovery.py` — crash recovery paths
   - `pytest tests/services/test_concurrent.py` — no deadlocks under concurrent submission
   - `python scripts/check_imports.py` — services don't import from db/ or backend/

5. **After Step 14-17** (backend + agents + prompts):
   - `pytest tests/backend/` — server health, auth, FastAPI TestClient
   - `pytest tests/agents/` — agent lifecycle, caching, resume
   - `pyright src/` — full project type-clean

6. **Full suite**:
   - `pre-commit run --all-files` — all formatters/linters happy
   - `python scripts/check_imports.py` — zero boundary violations
   - `pyright src/` — zero type errors
   - `pytest` — all tests pass
   - `pytest tests/test_architecture.py` — no bare excepts, no ORM model leaks, boundary enforcement

7. **Server smoke test**:
   - `uvicorn backend.edu_server:app --app-dir src` — starts cleanly
   - `GET /health` → 200
   - `GET /docs` → Swagger UI renders
   - `POST /token` with test creds → JWT returned
   - Activity record created in DB for each API call
