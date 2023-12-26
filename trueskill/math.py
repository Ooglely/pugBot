import numpy

BETA = 25 / 6


class Gaussian:
    def __init__(self, mean: float, deviation: float):
        self.mean: float = mean
        self.deviation: float = deviation

    def __add__(self, curve: "Gaussian") -> "Gaussian":
        return Gaussian(self.mean + curve.mean, self.deviation + curve.deviation)

    def __sub__(self, curve: "Gaussian") -> "Gaussian":
        return Gaussian(self.mean - curve.mean, self.deviation - curve.deviation)

    def calc(self, x: float) -> float:
        return (1 / (self.deviation * numpy.sqrt(2 * numpy.pi))) * numpy.exp(
            -0.5 * ((x - self.mean) / self.deviation) ** 2
        )


def integral(f, a, b, num):
    delta: float = float(b - a) / num
    result: float = 0.0
    for i in range(num):
        x = i * delta
        area = (f(x) * delta) + ((f(x + delta) - f(x)) * delta / 2)
        result += area
    return result


def erf(x: float) -> float:
    return (2 / numpy.sqrt(numpy.pi)) * integral(erf_func, 0, x, 1000)


def erf_func(x: float) -> float:
    return numpy.exp(-(x**2))


def cdf(delta: float, beta: float) -> float:
    return 0.5 * (1 + erf((delta) / (numpy.sqrt(2) * beta)))


def elo_change(winner: Gaussian, loser: Gaussian) -> float:
    return 1.0


print(cdf(1, 1) * 24)
