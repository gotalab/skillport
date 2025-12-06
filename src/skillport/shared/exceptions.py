"""Domain exceptions for SkillPort."""


class SkillPortError(Exception):
    """Base exception for SkillPort."""


class SkillNotFoundError(SkillPortError):
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Skill not found: {identifier}")


class AmbiguousSkillError(SkillPortError):
    def __init__(self, identifier: str, candidates: list[str]):
        self.identifier = identifier
        self.candidates = candidates
        super().__init__(f"Ambiguous skill: {identifier}. Candidates: {', '.join(candidates)}")


class ValidationError(SkillPortError):
    """Skill validation failed."""


class IndexingError(SkillPortError):
    """Index operation failed."""


class SourceError(SkillPortError):
    """Source (GitHub/local) operation failed."""


__all__ = [
    "SkillPortError",
    "SkillNotFoundError",
    "AmbiguousSkillError",
    "ValidationError",
    "IndexingError",
    "SourceError",
]
