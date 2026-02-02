import os
import math


class Calculator:
    """
    Simple calculator class.
    """

    def __init__(self, name):
        self.name = name

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def divide(self, a, b):
        if b == 0:
            return None
        return a / b


def factorial(n):
    """
    Calculate factorial using a loop.
    """
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def is_prime(number):
    if number <= 1:
        return False

    for i in range(2, int(math.sqrt(number)) + 1):
        if number % i == 0:
            return False
    return True
