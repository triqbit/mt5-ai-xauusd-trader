
import re
import time
import random
import string

def benchmark_masking_strategies(n_secrets=10, n_iterations=100000):
    secrets = [''.join(random.choices(string.ascii_letters + string.digits, k=20)) for _ in range(n_secrets)]
    mask = "[MASKED]"

    # Strategy 1: Current iterative approach
    def redact_iterative(data, secrets, mask):
        result = data
        for secret in secrets:
            if secret in result:
                result = result.replace(secret, mask)
        return result

    # Strategy 2: Regex approach
    secret_regex = re.compile("|".join(re.escape(s) for s in secrets))
    def redact_regex(data, regex, mask):
        return regex.sub(mask, data)

    # Sample data
    sample_text = "This is a log message without secrets. But here is one: " + secrets[0] + " and another " + secrets[-1]
    safe_text = "This is a perfectly safe log message with no secrets at all. It is quite long to make it realistic for performance testing."

    print(f"Benchmarking with {n_secrets} secrets, {n_iterations} iterations")

    # Test with secrets
    print("\nTest with secrets in text:")
    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = redact_iterative(sample_text, secrets, mask)
    print(f"Iterative: {(time.perf_counter() - start):.4f}s")

    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = redact_regex(sample_text, secret_regex, mask)
    print(f"Regex:     {(time.perf_counter() - start):.4f}s")

    # Test without secrets (the common case)
    print("\nTest with safe text (no secrets):")
    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = redact_iterative(safe_text, secrets, mask)
    print(f"Iterative: {(time.perf_counter() - start):.4f}s")

    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = redact_regex(safe_text, secret_regex, mask)
    print(f"Regex:     {(time.perf_counter() - start):.4f}s")

if __name__ == "__main__":
    benchmark_masking_strategies(n_secrets=5)
    benchmark_masking_strategies(n_secrets=20)
    benchmark_masking_strategies(n_secrets=50)
