# Command Parser System - Code Explanation

This document provides a brief explanation of the command parser system for handling slash commands in GitHub PR comments.

## Architecture Overview

The command parser system consists of three main components:

1. **Models** (`app/models/commands.py`) - Data structures
2. **Registry** (`app/commands/registry.py`) - Command definitions and validation
3. **Parser** (`app/commands/parser.py`) - Parsing logic

## Component Details

### 1. Command Models (`app/models/commands.py`)

**Purpose**: Define data structures for commands and errors.

**Key Classes**:

- **`Command`**: Represents a parsed command with all its context
  - `command`: Command name (e.g., "explain", "test")
  - `args`: List of positional arguments
  - `kwargs`: Dictionary of key=value arguments
  - `raw_text`: Original comment text
  - `user`: GitHub username
  - `pr_number`: Pull request number
  - `repo_name`: Repository name (owner/repo format)
  - Helper methods: `has_arg()`, `get_arg()`, `get_kwarg()`

- **`CommandError`**: Represents parsing or validation errors
  - `message`: Error description
  - `raw_text`: Original comment that caused error
  - `suggestion`: Helpful suggestion to fix the error

**Why**: Separates data structures from logic, making it easy to pass command information between functions.

---

### 2. Command Registry (`app/commands/registry.py`)

**Purpose**: Centralized registry of all available commands with metadata and validation rules.

**Key Classes**:

- **`CommandDefinition`**: Metadata for a single command
  - `name`: Command name
  - `description`: What the command does
  - `usage`: Usage example
  - `args_description`: Argument descriptions
  - `min_args`, `max_args`: Argument count constraints

- **`CommandRegistry`**: Manages all command definitions
  - `register()`: Add new commands
  - `get()`: Retrieve command by name
  - `exists()`: Check if command is valid
  - `list_commands()`: Get all commands
  - `get_help_text()`: Generate formatted help text
  - `validate_args()`: Validate argument counts

**Default Commands Registered**:
1. `/explain` - Explain file or class/function
2. `/explain-diff` - Explain PR changes
3. `/test` - Generate tests
4. `/generate-ci` - Generate CI/CD workflows
5. `/review` - Trigger full code review
6. `/help` - Show available commands

**Why**: Centralized command management makes it easy to add new commands without modifying parser logic. Validation rules are defined once per command.

**Global Instance**: `get_registry()` returns a singleton registry instance.

---

### 3. Command Parser (`app/commands/parser.py`)

**Purpose**: Extract and parse slash commands from GitHub comment text.

**Key Class**: `CommandParser`

**Main Methods**:

- **`parse_comment()`**: Main entry point for parsing
  - Takes: comment text, PR number, repo name, username
  - Returns: `Command` object or `CommandError`
  - Steps:
    1. Find command in text using regex
    2. Validate command exists in registry
    3. Parse arguments (handles quotes, key=value pairs)
    4. Validate argument count
    5. Return Command object with full context

- **`_find_command()`**: Regex-based command extraction
  - Pattern: `^\s*/([a-zA-Z0-9_-]+)(?:\s+(.+))?$`
  - Matches: `/command arg1 arg2`
  - Multiline: Finds commands anywhere in comment

- **`_parse_arguments()`**: Argument parsing with `shlex`
  - Handles: `arg1 arg2 "quoted arg" key=value`
  - Splits: positional args vs key=value kwargs
  - Respects: Single and double quotes

- **`_suggest_command()`**: Command suggestion for typos
  - Uses: Common prefix matching
  - Fallback: Suggests `/help`

- **`is_command()`**: Quick check if text contains valid command

**Convenience Function**: `parse_command()` - One-liner for parsing without creating parser instance.

**Why**: Uses battle-tested `shlex` for argument parsing (handles quotes, escaping). Regex pattern allows commands anywhere in comment text (middle, bottom, etc.).

---

## Usage Flow

### Example 1: Basic Command

```python
from app.commands.parser import parse_command

# User posts comment: "/explain app/main.py"
result = parse_command(
    comment_body="/explain app/main.py",
    pr_number=123,
    repo_name="user/repo",
    user="developer1"
)

if isinstance(result, Command):
    print(result.command)  # "explain"
    print(result.args)     # ["app/main.py"]
    # Process command...
else:  # CommandError
    print(result.message)
    print(result.suggestion)
```

### Example 2: Command with Multiple Arguments

```python
# User posts: "/test pytest --coverage"
result = parse_command(
    comment_body="/test pytest --coverage",
    pr_number=456,
    repo_name="org/project",
    user="tester"
)

# Result:
# result.command = "test"
# result.args = ["pytest", "--coverage"]
```

### Example 3: Command with Quoted Arguments

```python
# User posts: '/explain "app/utils/cache.py"'
result = parse_command(
    comment_body='/explain "app/utils/cache.py"',
    pr_number=789,
    repo_name="team/app",
    user="engineer"
)

# Result:
# result.command = "explain"
# result.args = ["app/utils/cache.py"]  # Quotes removed
```

### Example 4: Invalid Command

```python
# User posts: "/invalid"
result = parse_command(
    comment_body="/invalid",
    pr_number=999,
    repo_name="test/repo",
    user="user"
)

# Result is CommandError:
# result.message = "Unknown command: /invalid"
# result.suggestion = "Use /help to see available commands. Did you mean: help?"
```

---

## Integration Points

### Where to Use This System

1. **Webhook Handlers** (`app/webhooks/github.py`):
   ```python
   from app.commands.parser import parse_command

   # In issue_comment_event handler:
   result = parse_command(
       comment_body=comment.body,
       pr_number=pr_number,
       repo_name=repo_name,
       user=comment.user.login
   )

   if isinstance(result, CommandError):
       # Post error message to PR
       github_client.post_pr_comment(pr_number, str(result))
   else:
       # Route to appropriate handler
       await handle_command(result)
   ```

2. **Command Handlers** (new file to create):
   ```python
   async def handle_command(cmd: Command):
       if cmd.command == "explain":
           await handle_explain(cmd)
       elif cmd.command == "test":
           await handle_test(cmd)
       # ... etc
   ```

---

## Key Design Decisions

### 1. Why Dataclasses?
- Clean, typed data structures
- Automatic `__init__`, `__repr__`
- IDE autocomplete support
- Easy to extend

### 2. Why Separate Registry?
- Single source of truth for commands
- Easy to add commands without changing parser
- Centralized validation rules
- Can generate help text automatically

### 3. Why `shlex` for Parsing?
- Standard library (no dependencies)
- Handles shell-like quoting correctly
- Well-tested and robust
- Familiar syntax for developers

### 4. Why Return Union[Command, CommandError]?
- Explicit error handling
- Type-safe (with type hints)
- Caller must handle both cases
- No exceptions for expected errors

### 5. Why Regex for Command Extraction?
- Fast and efficient
- Multiline support
- Flexible (commands anywhere in comment)
- Simple pattern, easy to understand

---

## Extension Guide

### Adding a New Command

1. **Register in Registry** (`app/commands/registry.py`):
   ```python
   self.register(
       CommandDefinition(
           name="new-command",
           description="Description of what it does",
           usage="/new-command arg1 arg2",
           args_description="arg1: description\narg2: description",
           min_args=2,
           max_args=2,
       )
   )
   ```

2. **Create Handler** (in command handlers):
   ```python
   async def handle_new_command(cmd: Command):
       arg1 = cmd.get_arg(0)
       arg2 = cmd.get_arg(1)
       # Implementation...
   ```

3. **Route in Main Handler**:
   ```python
   if cmd.command == "new-command":
       await handle_new_command(cmd)
   ```

That's it! No changes needed to parser or models.

---

## Error Handling Strategy

The system uses **explicit error returns** instead of exceptions:

- **Expected errors** (invalid command, wrong args) → `CommandError`
- **Unexpected errors** (parsing failures) → `CommandError` with exception message
- **Critical errors** (system failures) → Allow exceptions to propagate

**Benefits**:
- Caller always knows to check type
- No try/except needed for expected cases
- Clear separation of error types
- Easy to post error messages to GitHub

---

## Testing Strategy

### Unit Tests (to create)

```python
# test_parser.py
def test_parse_valid_command():
    result = parse_command("/help", 1, "repo", "user")
    assert isinstance(result, Command)
    assert result.command == "help"

def test_parse_invalid_command():
    result = parse_command("/invalid", 1, "repo", "user")
    assert isinstance(result, CommandError)

def test_parse_with_arguments():
    result = parse_command("/explain app/main.py", 1, "repo", "user")
    assert result.args == ["app/main.py"]

def test_parse_quoted_arguments():
    result = parse_command('/explain "app/main.py"', 1, "repo", "user")
    assert result.args == ["app/main.py"]

def test_argument_validation():
    result = parse_command("/help extra", 1, "repo", "user")
    assert isinstance(result, CommandError)
```

---

## Performance Considerations

- **Regex compilation**: Pattern compiled once (class variable)
- **Registry singleton**: Created once, reused
- **Shlex parsing**: Fast for typical comment lengths
- **No database**: Stateless, in-memory only
- **No external calls**: Pure parsing logic

**Expected Performance**: <1ms for typical comments

---

## Security Considerations

### Handled by Design

1. **Command injection**: `shlex` safely handles quotes/escapes
2. **Regex DoS**: Simple pattern, no catastrophic backtracking
3. **Argument injection**: Arguments are parsed, not executed
4. **Command validation**: Only registered commands allowed

### Recommendations

- **Sanitize file paths** before file system access
- **Validate URLs** before external requests
- **Limit argument length** to prevent memory issues
- **Rate limit** command processing per user

---

## Summary

The command parser system provides:

✓ **Clean separation** of concerns (models, registry, parser)
✓ **Easy extensibility** for new commands
✓ **Robust parsing** with quote and argument support
✓ **Clear error handling** with helpful messages
✓ **Type-safe** with dataclasses and type hints
✓ **Zero dependencies** (uses standard library)
✓ **Fast and efficient** for production use

**Next Steps**: Integrate with webhook handlers and create command execution logic.
