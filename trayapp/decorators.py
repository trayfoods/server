import time

# get the time complexity of a function
def get_time_complexity(fn):
    """
    A decorator to get the time complexity of a function
    """
    def inner(*args, **kwargs):
        start_time = time.time()
        result = fn(*args, **kwargs)
        end_time = time.time()
        print(f"Time taken to execute {fn.__name__} is {end_time - start_time}")
        return result

    return inner