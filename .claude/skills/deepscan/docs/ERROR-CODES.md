# DeepScan Error Code Reference

All DeepScan errors follow the format `[DS-NNN] Title: message` with an optional `Suggestion:` remediation hint.

> **Note**: The `doc_url` property in error messages generates URLs like `https://deepscan.io/docs/errors/DS-NNN`. These URLs do not currently resolve. Use this document as the authoritative error reference.

## Error Categories

| Code Range | Category | Exit Code | Description |
|------------|----------|-----------|-------------|
| DS-0xx | Validation | 2 | Invalid user input (bad path, bad chunk size, missing query) |
| DS-1xx | Parsing | 3 | Failed to parse code, JSON, checkpoint, or sub-agent response |
| DS-2xx | Chunking | 4 | Chunk creation or aggregation problems |
| DS-3xx | Resource | 5 | File not found, permission denied, size limits exceeded |
| DS-4xx | Configuration | 6 | Configuration file or setting errors |
| DS-5xx | System | 1 | Internal errors, timeouts, rate limits |
| DS-505 | System (cancelled) | 130 | User cancellation (128 + SIGINT, Unix convention) |

---

## DS-0xx: Input / Validation

### DS-001: Invalid Context Path

**Category:** Validation | **Exit code:** 2

**What happened:** The path provided to `init` does not exist or is not accessible.

**Common causes:**
- Typo in the directory or file path
- Path is relative and the working directory is wrong
- Permissions prevent access

**Fix:** Verify the path exists with `ls <path>`. Use an absolute path if relative paths cause issues.

---

### DS-002: Invalid Session Hash

**Category:** Validation | **Exit code:** 2

**What happened:** The session hash contains invalid characters.

**Common causes:**
- Manually typed hash with a typo
- Copy-paste error that included extra whitespace

**Fix:** Session hashes must contain only alphanumeric characters, underscores, and hyphens. Use `list` to see available session hashes and copy the exact value.

---

### DS-003: Missing Query

**Category:** Validation | **Exit code:** 2

**What happened:** No analysis query was provided during initialization.

**Common causes:**
- Forgot the `-q` flag

**Fix:** Provide a query with `-q/--query`: `init <path> -q "your analysis question"`

---

### DS-004: Invalid Chunk Size

**Category:** Validation | **Exit code:** 2

**What happened:** The chunk size is outside the allowed range.

**Common causes:**
- Value below 50,000 or above 300,000 characters

**Fix:** Use a chunk size between 50,000 and 300,000: `write_chunks(size=150000)`

---

### DS-005: Overlap Exceeds Size

**Category:** Validation | **Exit code:** 2

**What happened:** The chunk overlap is equal to or greater than the chunk size.

**Common causes:**
- Overlap set too high relative to chunk size
- Overlap exceeds 50,000 characters (hard cap)

**Fix:** Set overlap to less than the chunk size and under 50,000: `write_chunks(size=150000, overlap=10000)`

---

### DS-006: Empty Context

**Category:** Validation | **Exit code:** 2

**What happened:** No analyzable files were found in the given path.

**Common causes:**
- Path points to an empty directory
- All files are excluded by `.deepscanignore` or default prune directories
- Only binary files in the directory

**Fix:** Check that the path contains source files. Review your `.deepscanignore` patterns. DeepScan auto-excludes 19 directories including `node_modules`, `.git`, `__pycache__`, and `dist`.

---

## DS-1xx: Parsing / Processing

### DS-101: AST Parse Failed

**Category:** Parsing | **Exit code:** 3

**What happened:** Tree-sitter failed to parse a file for semantic chunking.

**Common causes:**
- Syntax errors in the source file
- Unsupported language (only Python, JavaScript, TypeScript, Java, Go supported)
- Corrupted file encoding

**Fix:** Disable semantic chunking with `write_chunks(size=150000, semantic=False)`. The system falls back to text-based chunking automatically.

---

### DS-102: JSON Decode Error

**Category:** Parsing | **Exit code:** 3

**What happened:** A JSON file could not be parsed.

**Common causes:**
- Malformed JSON in state, checkpoint, or result files
- File was partially written due to a crash

**Fix:** Verify the JSON file with a linter. If a state file is corrupted, delete the session with `abort <hash>` and start fresh.

---

### DS-103: Encoding Error

**Category:** Parsing | **Exit code:** 3

**What happened:** A file could not be decoded as UTF-8.

**Common causes:**
- Binary file detected as text
- File uses non-UTF-8 encoding (e.g., Latin-1, Shift-JIS)

**Fix:** Ensure source files are UTF-8 encoded. Add binary files to `.deepscanignore`.

---

### DS-104: Sub-agent Parse Failed

**Category:** Parsing | **Exit code:** 3

**What happened:** A sub-agent returned a response that could not be parsed as structured JSON.

**Common causes:**
- Sub-agent produced malformed output
- Response did not include the expected JSON code block

**Fix:** Re-run the chunk. If persistent, check the chunk content for unusual formatting that may confuse the sub-agent.

---

### DS-105: Checkpoint Corrupt

**Category:** Parsing | **Exit code:** 3

**What happened:** The checkpoint file is corrupted and cannot be loaded.

**Common causes:**
- Process was killed during checkpoint write
- Disk full during write operation

**Fix:** Delete the checkpoint and restart the session. The session state (`state.json`) may still be intact -- try `resume <hash>`.

---

## DS-2xx: Chunking / Aggregation

### DS-201: Chunk Too Large

**Category:** Chunking | **Exit code:** 4

**What happened:** A single chunk exceeds the maximum allowed size.

**Common causes:**
- Very large file that cannot be split further
- Semantic chunking produced an oversized AST node

**Fix:** Reduce the chunk size parameter or split the large file. Add the file to `.deepscanignore` if it does not need analysis.

---

### DS-202: No Chunks Created

**Category:** Chunking | **Exit code:** 4

**What happened:** The chunking operation produced zero chunks.

**Common causes:**
- Context is empty after filtering
- All files were excluded

**Fix:** Verify the context contains files with `context_length()`. Check that `.deepscanignore` is not too aggressive.

---

### DS-203: Aggregation Conflict

**Category:** Chunking | **Exit code:** 4

**What happened:** Sub-agents returned conflicting results that could not be automatically resolved.

**Common causes:**
- Ambiguous code that different sub-agents interpreted differently

**Fix:** Review the conflicting findings manually. The `reduce` output lists detected contradictions.

---

### DS-204: Result Validation Failed

**Category:** Chunking | **Exit code:** 4

**What happened:** A sub-agent result did not match the expected `ChunkResult` schema.

**Common causes:**
- Missing required fields (`chunk_id`, `status`, `findings`, `missing_info`)
- Invalid field types

**Fix:** Ensure results follow the schema: `{"chunk_id": "...", "status": "completed", "findings": [...], "missing_info": [], "partial_answer": null}`

---

### DS-205: Batch Failed

**Category:** Chunking | **Exit code:** 4

**What happened:** An entire batch of chunks failed after retries.

**Common causes:**
- Repeated API failures
- All chunks in the batch produced errors

**Fix:** Check network connectivity. Try running with fewer parallel agents or in sequential mode.

---

## DS-3xx: Resource / File

### DS-301: File Not Found

**Category:** Resource | **Exit code:** 5

**What happened:** A referenced file does not exist on disk.

**Common causes:**
- File was deleted after scan initialization
- Path mismatch between scan context and current filesystem

**Fix:** Verify the file exists. Re-run `init` if the filesystem has changed.

---

### DS-302: Permission Denied

**Category:** Resource | **Exit code:** 5

**What happened:** Insufficient permissions to read or write a file.

**Common causes:**
- File owned by a different user
- Read-only filesystem

**Fix:** Check file permissions with `ls -la <path>`. Ensure the cache directory (`~/.claude/cache/deepscan/`) is writable.

---

### DS-303: File Too Large

**Category:** Resource | **Exit code:** 5

**What happened:** A single file exceeds the 10MB size limit.

**Common causes:**
- Large generated files, database dumps, or binary files in the scan path

**Fix:** Files over 10MB are automatically skipped during `init`. Add them to `.deepscanignore` to suppress the warning.

---

### DS-304: Context Too Large

**Category:** Resource | **Exit code:** 5

**What happened:** The total context size exceeds the 50MB limit.

**Common causes:**
- Scanning a very large codebase in full mode

**Fix:** Use `--lazy` mode to explore the structure first, then `--target` to scan specific directories. Add non-essential files to `.deepscanignore`.

---

### DS-305: Cache Directory Error

**Category:** Resource | **Exit code:** 5

**What happened:** Cannot create or access the cache directory at `~/.claude/cache/deepscan/`.

**Common causes:**
- Disk full
- Permission issues on the home directory
- Filesystem is read-only

**Fix:** Check disk space (`df -h`) and directory permissions. Ensure `~/.claude/cache/` is writable.

---

### DS-306: Session Not Found

**Category:** Resource | **Exit code:** 5

**What happened:** The requested session does not exist.

**Common causes:**
- Session was cleaned up by `clean` or deleted by `abort`
- Typo in session hash
- Session was created in a different project/directory

**Fix:** Run `list` to see available sessions. If no sessions exist, run `init` to create a new one.

---

## DS-4xx: Configuration

### DS-401: Invalid Config File

**Category:** Configuration | **Exit code:** 6

**What happened:** A configuration file has syntax errors.

**Common causes:**
- Malformed YAML or JSON in config file

**Fix:** Validate the config file with a JSON/YAML linter.

---

### DS-402: Missing Required Setting

**Category:** Configuration | **Exit code:** 6

**What happened:** A required configuration setting is missing.

**Common causes:**
- Incomplete configuration

**Fix:** Check the [Reference](REFERENCE.md#configuration-settings) for required settings and their defaults.

---

### DS-403: Invalid Model Setting

**Category:** Configuration | **Exit code:** 6

**What happened:** An unsupported model was specified.

**Common causes:**
- Typo in model name

**Fix:** Supported models are `haiku` and `sonnet`.

---

### DS-404: Escalation Budget Exceeded

**Category:** Configuration | **Exit code:** 6

**What happened:** The model escalation budget has been exhausted for this session.

**Common causes:**
- More than 15% of chunks required escalation to sonnet
- Sonnet cost exceeded $5 for the session

**Fix:** Increase `max_escalation_ratio` or `max_sonnet_cost_usd` in the configuration. Alternatively, manually re-run failed chunks.

---

## DS-5xx: System / Internal

### DS-501: Internal Error

**Category:** System | **Exit code:** 1

**What happened:** An unexpected error occurred that does not fit other categories.

**Common causes:**
- Bug in DeepScan
- Unexpected system state

**Fix:** Report this issue with the full error message and traceback.

---

### DS-502: State Corruption

**Category:** System | **Exit code:** 1

**What happened:** The session state file is corrupted and cannot be loaded.

**Common causes:**
- Process killed during state write
- Disk corruption
- Manual editing of `state.json`

**Fix:** Delete the session with `abort <hash>` and start a new scan. Previously exported results are not affected.

---

### DS-503: Timeout Error

**Category:** System | **Exit code:** 1

**What happened:** An operation exceeded the allowed time limit.

**Common causes:**
- REPL expression took longer than the 5-second default timeout
- `write_chunks` exceeded the dynamic timeout (30-120 seconds based on context size)
- Complex regex in `grep()` hit the 10-second ReDoS protection timeout

**Fix:** Use `--timeout N` to increase the timeout: `exec -c "..." --timeout 30`. For grep, simplify the regex pattern.

---

### DS-504: Rate Limit Error

**Category:** System | **Exit code:** 1

**What happened:** The API rate limit was exceeded during sub-agent processing.

**Common causes:**
- Too many parallel agents
- Rapid successive API calls

**Fix:** Wait and retry. Reduce `max_parallel_agents` if the problem persists.

---

### DS-505: Cancelled By User

**Category:** System | **Exit code:** 130

**What happened:** The operation was cancelled by the user (Ctrl+C).

**Common causes:**
- User pressed Ctrl+C during a scan

**Fix:** Resume the scan with `resume <session_hash>`. Completed batches are preserved. See [Troubleshooting](TROUBLESHOOTING.md#how-to-resume-an-interrupted-scan) for details.

> **Note**: The remediation template in the source code suggests `deepscan --resume {session_id}`. The correct command is `resume <session_hash>`.

---

## Quick Lookup Table

| Code | Title | Category | Exit Code |
|------|-------|----------|-----------|
| DS-001 | Invalid Context Path | Validation | 2 |
| DS-002 | Invalid Session Hash | Validation | 2 |
| DS-003 | Missing Query | Validation | 2 |
| DS-004 | Invalid Chunk Size | Validation | 2 |
| DS-005 | Overlap Exceeds Size | Validation | 2 |
| DS-006 | Empty Context | Validation | 2 |
| DS-101 | AST Parse Failed | Parsing | 3 |
| DS-102 | JSON Decode Error | Parsing | 3 |
| DS-103 | Encoding Error | Parsing | 3 |
| DS-104 | Sub-agent Parse Failed | Parsing | 3 |
| DS-105 | Checkpoint Corrupt | Parsing | 3 |
| DS-201 | Chunk Too Large | Chunking | 4 |
| DS-202 | No Chunks Created | Chunking | 4 |
| DS-203 | Aggregation Conflict | Chunking | 4 |
| DS-204 | Result Validation Failed | Chunking | 4 |
| DS-205 | Batch Failed | Chunking | 4 |
| DS-301 | File Not Found | Resource | 5 |
| DS-302 | Permission Denied | Resource | 5 |
| DS-303 | File Too Large | Resource | 5 |
| DS-304 | Context Too Large | Resource | 5 |
| DS-305 | Cache Directory Error | Resource | 5 |
| DS-306 | Session Not Found | Resource | 5 |
| DS-401 | Invalid Config File | Config | 6 |
| DS-402 | Missing Required Setting | Config | 6 |
| DS-403 | Invalid Model Setting | Config | 6 |
| DS-404 | Escalation Budget Exceeded | Config | 6 |
| DS-501 | Internal Error | System | 1 |
| DS-502 | State Corruption | System | 1 |
| DS-503 | Timeout Error | System | 1 |
| DS-504 | Rate Limit Error | System | 1 |
| DS-505 | Cancelled By User | System | 130 |

---

## See Also

- [Troubleshooting](TROUBLESHOOTING.md) -- common errors organized by symptom with step-by-step fixes
- [Reference](REFERENCE.md) -- complete command and configuration reference
