.DEFAULT_GOAL := help
.PHONY: help build-dist publish publish-test publish-check publish-test-check

help:
	@printf '%s\n' 'make build-dist' 'make publish-check / make publish-test-check (dry run only)' 'make publish / make publish-test (uploads packages)'

# Build without any publishing credential in the build process.
build-dist:
	uv build --out-dir dist/ --clear packages/skillport-core
	uv build --out-dir dist/ .
	uv build --out-dir dist/ packages/skillport-mcp

publish: build-dist
	OP_BIOMETRIC_UNLOCK_ENABLED=$${OP_BIOMETRIC_UNLOCK_ENABLED:-true} op run --env-file=.env.publish-pypi -- uv publish --publish-url=https://upload.pypi.org/legacy/ --trusted-publishing=never

publish-test: build-dist
	OP_BIOMETRIC_UNLOCK_ENABLED=$${OP_BIOMETRIC_UNLOCK_ENABLED:-true} op run --env-file=.env.publish-testpypi -- uv publish --publish-url=https://test.pypi.org/legacy/ --trusted-publishing=never

publish-check: build-dist
	OP_BIOMETRIC_UNLOCK_ENABLED=$${OP_BIOMETRIC_UNLOCK_ENABLED:-true} op run --env-file=.env.publish-pypi -- uv publish --publish-url=https://upload.pypi.org/legacy/ --trusted-publishing=never --dry-run

publish-test-check: build-dist
	OP_BIOMETRIC_UNLOCK_ENABLED=$${OP_BIOMETRIC_UNLOCK_ENABLED:-true} op run --env-file=.env.publish-testpypi -- uv publish --publish-url=https://test.pypi.org/legacy/ --trusted-publishing=never --dry-run
