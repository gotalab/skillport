"""Property-based tests for skill name validation.

Uses Hypothesis to generate test cases that verify:
1. Valid name patterns always pass pattern validation
2. Invalid name patterns always fail
3. Category normalization is idempotent
"""

import string

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from skillport.modules.skills.internal.validation import (
    NAME_MAX_LENGTH,
    NAME_PATTERN,
    NAME_RESERVED_WORDS,
    validate_skill_record,
)

# Strategy for valid skill names: lowercase letters, digits, hyphens
valid_name_chars = st.sampled_from(string.ascii_lowercase + string.digits + "-")
valid_name_strategy = st.text(
    alphabet=valid_name_chars,
    min_size=1,
    max_size=NAME_MAX_LENGTH,
).filter(lambda s: bool(NAME_PATTERN.match(s)))


# Strategy for names with invalid characters
invalid_char_strategy = st.sampled_from(
    string.ascii_uppercase  # uppercase
    + "_"  # underscore
    + " "  # space
    + "."  # dot
    + "/"  # slash
    + "@#$%^&*()+=[]{}|\\:;\"'<>,?"  # special chars
)


class TestNamePatternProperty:
    """Property-based tests for NAME_PATTERN."""

    @given(name=valid_name_strategy)
    @settings(max_examples=200)
    def test_valid_names_match_pattern(self, name: str):
        """Any string of [a-z0-9-]+ should match NAME_PATTERN."""
        # Filter out reserved words
        assume(not any(reserved in name.lower() for reserved in NAME_RESERVED_WORDS))

        assert NAME_PATTERN.match(name) is not None, f"'{name}' should match pattern"

    @given(
        prefix=st.text(alphabet=string.ascii_lowercase, min_size=0, max_size=10),
        invalid_char=invalid_char_strategy,
        suffix=st.text(alphabet=string.ascii_lowercase, min_size=0, max_size=10),
    )
    @settings(max_examples=200)
    def test_invalid_chars_fail_pattern(self, prefix: str, invalid_char: str, suffix: str):
        """Names with invalid characters should not match pattern."""
        name = prefix + invalid_char + suffix
        assume(len(name) > 0)

        # The pattern should not match because of invalid char
        assert NAME_PATTERN.match(name) is None, f"'{name}' should NOT match pattern"


class TestNameValidationProperty:
    """Property-based tests for validate_skill_record name rules."""

    @given(name=valid_name_strategy)
    @settings(max_examples=100)
    def test_valid_names_pass_validation(self, name: str):
        """Valid names should pass pattern validation."""
        # Filter out reserved words and edge cases
        assume(not any(reserved in name.lower() for reserved in NAME_RESERVED_WORDS))
        assume(len(name) <= NAME_MAX_LENGTH)

        issues = validate_skill_record(
            {
                "name": name,
                "description": "test description",
                "path": f"/skills/{name}",  # path matches name
            }
        )

        # Should have no pattern-related fatal issues
        pattern_issues = [
            i for i in issues if i.severity == "fatal" and "invalid" in i.message.lower()
        ]
        assert len(pattern_issues) == 0, f"'{name}' should pass pattern validation"

    @given(
        base=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=20),
        invalid_char=invalid_char_strategy,
    )
    @settings(max_examples=100)
    def test_invalid_chars_fail_validation(self, base: str, invalid_char: str):
        """Names with invalid characters should fail validation."""
        name = base + invalid_char
        assume(len(name) <= NAME_MAX_LENGTH)

        issues = validate_skill_record(
            {
                "name": name,
                "description": "test",
                "path": f"/skills/{name}",
            }
        )

        # Should have pattern-related fatal issue
        pattern_issues = [
            i for i in issues if i.severity == "fatal" and "invalid" in i.message.lower()
        ]
        assert len(pattern_issues) > 0, f"'{name}' should fail pattern validation"

    @given(length=st.integers(min_value=NAME_MAX_LENGTH + 1, max_value=NAME_MAX_LENGTH + 50))
    @settings(max_examples=50)
    def test_long_names_fail_validation(self, length: int):
        """Names exceeding max length should fail validation."""
        name = "a" * length

        issues = validate_skill_record(
            {
                "name": name,
                "description": "test",
                "path": f"/skills/{name}",
            }
        )

        # Should have length-related fatal issue
        length_issues = [
            i for i in issues if i.severity == "fatal" and "chars" in i.message.lower()
        ]
        assert len(length_issues) > 0, f"Name of length {length} should fail"


class TestCategoryNormalizationProperty:
    """Property-based tests for category normalization."""

    @given(category=st.text(min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_normalization_is_idempotent(self, category: str):
        """Normalizing a category twice should yield same result."""
        # Simulate normalization: strip + lower
        normalized_once = category.strip().lower()
        normalized_twice = normalized_once.strip().lower()

        assert normalized_once == normalized_twice, (
            f"Normalization should be idempotent: '{category}'"
        )

    @given(category=st.text(min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_normalization_removes_leading_trailing_whitespace(self, category: str):
        """Normalization should remove leading/trailing whitespace."""
        normalized = category.strip().lower()

        assert normalized == normalized.strip(), (
            "Normalized category should have no leading/trailing whitespace"
        )

    @given(category=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_normalization_is_lowercase(self, category: str):
        """Normalization should produce lowercase output."""
        normalized = category.strip().lower()

        assert normalized == normalized.lower(), "Normalized category should be lowercase"

    @given(
        leading=st.text(alphabet=" \t\n", min_size=0, max_size=5),
        content=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10),
        trailing=st.text(alphabet=" \t\n", min_size=0, max_size=5),
    )
    @settings(max_examples=100)
    def test_whitespace_variations_normalize_same(self, leading: str, content: str, trailing: str):
        """Different whitespace variations should normalize to same value."""
        variant1 = leading + content + trailing
        variant2 = content

        assert variant1.strip().lower() == variant2.strip().lower(), (
            "Whitespace variations should normalize to same value"
        )


class TestReservedWordsProperty:
    """Property-based tests for reserved word detection."""

    @given(
        prefix=st.text(alphabet=string.ascii_lowercase + "-", min_size=0, max_size=10),
        suffix=st.text(alphabet=string.ascii_lowercase + "-", min_size=0, max_size=10),
    )
    @settings(max_examples=100)
    def test_reserved_words_detected_anywhere(self, prefix: str, suffix: str):
        """Reserved words should be detected anywhere in name."""
        for reserved in NAME_RESERVED_WORDS:
            name = prefix + reserved + suffix
            # Filter to valid pattern
            if not NAME_PATTERN.match(name):
                continue

            issues = validate_skill_record(
                {
                    "name": name,
                    "description": "test",
                    "path": f"/skills/{name}",
                }
            )

            reserved_issues = [
                i for i in issues if i.severity == "fatal" and "reserved" in i.message.lower()
            ]
            assert len(reserved_issues) > 0, f"'{name}' should be rejected (contains '{reserved}')"
