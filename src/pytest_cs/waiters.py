import time
from types import TracebackType
from typing import Final, Generic, TypeVar

from _pytest.outcomes import Failed

from .helpers import default_timeout


T = TypeVar("T")


# Implement a constuct to wait for any condition to be true without a busy loop.
# It must be subclassed to return the context.
#
# Example:
#
#  for waiter in some_waiter(params, timeout=2):
#    with waiter as ctx:
#       assert ctx.some_condition()
#       assert ctx.some_other_condition()
#       assert ctx.yet_another_condition()
class WaiterGenerator(Generic[T]):
    def __init__(self, timeout: float | None = None, step: float = 0.1) -> None:
        if timeout is None:
            timeout = default_timeout()
        self.start: Final = time.monotonic()
        self.timeout: float = timeout
        self.step: Final = step  # wait between iterations
        self.done: bool = False  # set to True to stop the iteration
        self.failure: BaseException | None = None  # capture an exception to raise on the last iteration
        self.iteration: int = 0  # for debugging

    # Yield a context manager until the timeout is reached.
    #
    # When a with: block is executed with no exceptions that
    # could indicate a test failure, the iteration is stopped.
    # The test is on its way to success :)
    #
    # If there were exceptions (of type AssertionError or Failed)
    # the iteration is continued until the timeout is reached.
    #
    # On its last iteration before the timeout, any exception
    # is allowed to propagate and will cause the test to fail.
    def __iter__(self):
        while not self.done and (self.start + self.timeout > time.monotonic()):
            self.refresh()
            yield self
            time.sleep(self.step)
            self.timeout -= self.step
            self.iteration += 1

            # until the last iteration, we ignore test failures
            if self.failure and not isinstance(self.failure, AssertionError) and not isinstance(self.failure, Failed):
                raise self.failure

        if self.done:
            return True

        if self.failure:
            raise self.failure

    def context(self) -> T:
        """Return the context from the context manager. Subclasses override this to return the actual T (e.g. a Probe)."""
        raise NotImplementedError

    # this is called before each iteration to refresh the state
    # of the object: reload a container, etc.
    def refresh(self):
        pass

    # Enter the with: block
    # self.failure is reset because we only care about the last failure
    # (i.e. the one that caused the timeout)
    def __enter__(self) -> T:
        self.failure = None
        return self.context()

    # Exit the with: block
    # if there was no exception, we set self.done to True to stop the iteration
    # otherwise, we capture the exception
    # we always return True to prevent the exception from propagating
    # (we'll raise it on the last iteration)
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            self.done = True
        else:
            self.failure = exc_val

        return True
