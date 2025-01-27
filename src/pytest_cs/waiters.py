import time

from _pytest.outcomes import Failed

from .helpers import get_timeout


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
class WaiterGenerator:
    def __init__(self, timeout=get_timeout(), step=.1):
        self.start = time.monotonic()
        self.timeout = timeout
        self.step = step        # wait between iterations
        self.done = False       # set to True to stop the iteration
        self.failure = None     # capture an exception to raise on the last iteration
        self.iteration = 0      # for debugging

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
            if (self.failure and not isinstance(self.failure, AssertionError)
                    and not isinstance(self.failure, Failed)):
                raise self.failure

        if self.done:
            return True

        if self.failure:
            raise self.failure

    # this is returned by the context manager.
    def context(self):
        raise NotImplementedError

    # this is called before each iteration to refresh the state
    # of the object: reload a container, etc.
    def refresh(self):
        pass

    # Enter the with: block
    # self.failure is reset because we only care about the last failure
    # (i.e. the one that caused the timeout)
    def __enter__(self):
        self.failure = None
        return self.context()

    # Exit the with: block
    # if there was no exception, we set self.done to True to stop the iteration
    # otherwise, we capture the exception
    # we always return True to prevent the exception from propagating
    # (we'll raise it on the last iteration)
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done = True
        else:
            self.failure = exc_val

        return True
