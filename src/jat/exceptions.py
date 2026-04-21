class JatError(Exception):
    pass


class JulesApiError(JatError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Jules API {status_code}: {message}")


class GitHubApiError(JatError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API {status_code}: {message}")


class AccountPoolExhausted(JatError):
    pass


class WorkflowValidationError(JatError):
    pass


class DependencyTimeoutError(JatError):
    pass
