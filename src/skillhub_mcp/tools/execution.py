import subprocess
from typing import Dict, Any, List
from ..config import settings
from ..db import SkillDB
from ..utils import validate_path, is_skill_enabled, is_command_allowed

class ExecutionTools:
    """Tool implementations for file read and command execution."""

    def __init__(self, db: SkillDB):
        self.db = db
        self.settings = getattr(db, "settings", settings)

    def read_skill_file(self, skill_name: str, file_path: str) -> Dict[str, Any]:
        """Read a file from the skill's directory."""
        # 1. Check enabled
        record = self.db.get_skill(skill_name)
        if not record:
            raise ValueError(f"Skill not found: {skill_name}")

        if not is_skill_enabled(skill_name, record.get("category"), settings_obj=self.settings):
            raise ValueError(f"Skill is disabled: {skill_name}")

        # 2. Validate path (security)
        full_path = validate_path(skill_name, file_path, settings_obj=self.settings)

        # 3. Check size
        try:
            file_size = full_path.stat().st_size
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")

        max_bytes = self.settings.max_file_bytes
        truncated = False

        content = ""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                if file_size > max_bytes:
                    content = f.read(max_bytes)
                    truncated = True
                else:
                    content = f.read()
        except UnicodeDecodeError:
            # Fallback for binary? PRD implies text "read_skill_file ... templates ...".
            # Return error or hex? PRD: "content: ... string".
            raise ValueError("File is not UTF-8 text")

        return {
            "content": content,
            "encoding": "utf-8",
            "truncated": truncated,
        }

    def execute_skill_command(self, skill_name: str, command: str, args: List[str] = []) -> Dict[str, Any]:
        """
        Execute a command within the skill's directory.
        """
        # 1. Check enabled
        record = self.db.get_skill(skill_name)
        if not record:
            raise ValueError(f"Skill not found: {skill_name}")
        if not is_skill_enabled(skill_name, record.get("category"), settings_obj=self.settings):
            raise ValueError(f"Skill is disabled: {skill_name}")

        # 2. Check command allowlist
        if not is_command_allowed(command, settings_obj=self.settings):
            raise ValueError(f"Command not allowed: {command}")

        # 3. Prepare execution
        skill_dir = self.settings.get_effective_skills_dir() / skill_name
        if not skill_dir.exists():
            raise ValueError(f"Skill directory not found: {skill_dir}")
            
        # 4. Execute
        # Timeout and Max Output
        timeout_sec = self.settings.exec_timeout_seconds
        max_bytes = self.settings.exec_max_output_bytes
        
        cmd_list = [command] + args
        
        try:
            # Capture output
            # We can't easily limit capture size in subprocess.run during execution without using Popen and manual reading.
            # subprocess.run captures all then we truncate. 
            # If output is huge, it might consume memory. 
            # For v0.0.0, capturing all then truncating is acceptable unless it blows OOM.
            # PRD says "output ... exceeding ... truncated".
            
            proc = subprocess.run(
                cmd_list,
                cwd=skill_dir,
                capture_output=True,
                text=True, # Treat as text (utf-8)
                timeout=timeout_sec,
                shell=False
            )
            
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
            is_timeout = False
            
        except subprocess.TimeoutExpired as e:
            # Killed
            stdout = e.stdout if e.stdout else ""
            stderr = e.stderr if e.stderr else ""
            exit_code = -1
            is_timeout = True
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution failed: {e}",
                "exit_code": -1,
                "timeout": False,
                "truncated": {"stdout": False, "stderr": False}
            }

        # Truncate by byte length to honor exec_max_output_bytes
        trunc_stdout = False
        trunc_stderr = False

        def _truncate_to_bytes(text: str):
            data = text.encode("utf-8")
            if len(data) <= max_bytes:
                return text, False
            truncated = data[:max_bytes]
            return truncated.decode("utf-8", errors="replace"), True
        
        stdout, trunc_stdout = _truncate_to_bytes(stdout)
        stderr, trunc_stderr = _truncate_to_bytes(stderr)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "timeout": is_timeout,
            "truncated": {
                "stdout": trunc_stdout,
                "stderr": trunc_stderr
            }
        }
