import secrets
from typing import NamedTuple

import numpy as np

# Although `Point` is usually imported from `utilities.geometry`, defining it again
# here avoids a circular import error when running `utilities.ocr` directly for testing.
Point = NamedTuple("Point", x=int, y=int)


def random_point_around(point: Point, xpad: int, ypad: int) -> Point:
    """Return a pixel coordinate drawn from a Gaussian bell around a point.

    Args:
        point (Point): The point around which a normal sample will be drawn.
        xpad (int): How much x-padding (in pixels) to include around the given point.
        ypad (int): How much y-padding (in pixels) to include around the given point.

    Returns:
        Point:  Point: A random pixel coordinate sampled from around the given point.
    """
    return random_point_in(
        xmin=point.x - xpad, ymin=point.y - ypad, width=2 * xpad, height=2 * ypad
    )


def random_point_in(xmin: int, ymin: int, width: int, height: int) -> Point:
    """Return a pixel coordinate drawn from a Gaussian bell within a bounding box.

    Args:
        xmin (int): The left-most coordinate of the bounding box.
        ymin (int): The top-most coordinate of the bounding box.
        width (int): The width of the bounding box.
        height (int): The height of the bounding box.

    Returns:
        Point: A random pixel coordinate within the bounding box.
    """
    rng = secrets.SystemRandom()
    # Calculate the dimensions and position of an inner bounding box within the full
    # bounding box. This padding improves reliability.
    padding_factor = rng.uniform(0.10, 0.15)
    inner_xmin = round(xmin + width * padding_factor)
    inner_ymin = round(ymin + height * padding_factor)
    inner_width = round(width * (1.000 - (padding_factor * 2)))
    inner_height = round(height * (1.000 - (padding_factor * 2)))
    return __random_from(inner_xmin, inner_ymin, inner_width, inner_height)


def __random_from(xmin: int, ymin: int, width: int, height: int) -> Point:
    """Generate a random pixel within a bounding box.

    Note that the bounding box can either be centered on the xmin and ymin
    coordinates, or it can be offset from these coordinates (i.e., xmin and ymin
    represent the top-left corner of the bounding box).

    Args:
        xmin: The left-most coordinate of the bounding box, measured in pixels.
        ymin: The top-most coordinate of the bounding box, measured in pixels.
        width: The width of the bounding box in pixels.
        height: The height of the bounding box in pixels.

    Returns:
        Point: A randomly generated point within a bounding box.
    """
    # Calculate maximum values for x and y within the bounding box.
    xmax = xmin + width
    ymax = ymin + height

    # Calculate the center of the bounding box.
    x_center = xmin + round((xmax - xmin) / 2)
    y_center = ymin + round((ymax - ymin) / 2)

    # Calculate standard deviations for x and y based on bounding box dimensions.
    xstd = width / 6
    ystd = height / 6

    # Sample a coordinate from a truncated Gaussian bell defined by the bounding box.
    x = round(trunc_norm_samp(xmin, xmax, x_center, xstd))
    y = round(trunc_norm_samp(ymin, ymax, y_center, ystd))
    return Point(x, y)


def trunc_norm_samp(lo: float, hi: float, mean=None, std=None) -> float:
    """Generate a random sample from a truncated normal distribution.

    Note that a standard deviation of 1/6 the mean is recommended. This allows for the
    99.7% of the sampled points to fall within 3 standard deviations of the mean,
    fitting near-perfectly within the bounding box dimensions.

    Args:
        lo (float): The lower bound of the truncated normal distribution.
        hi (float): The upper bound of the truncated normal distribution.
        mean (float, optional): The mean of the normal distribution. Defaults to the
            midpoint is mid-point between the `lo` and `hi`.
        std (float, optional): The standard deviation of the normal distribution.
            Defaults to 1/6 of the distance between the `lo` and `hi`.

    Returns:
        float: A random float from the truncated normal distribution.
    Examples:
        100,000 x `truncated_normal_sample(0, 100)` graphed:
            src/img/explanatory/trunc-norm-samp-100k.png
    """
    mean = (lo + hi) / 2 if mean is None else mean
    std = (hi - lo) / 6 if std is None else std
    rng = secrets.SystemRandom()
    sample = rng.gauss(mean, std)
    while sample < lo or sample > hi:
        sample = rng.gauss(mean, std)
    return sample


def biased_trunc_norm_samp(lo: float, hi: float, prefer_hi: bool = False) -> float:
    """Generate a truncated normal sample with enhanced randomization.

    Generate a random sample from a truncated normal distribution derived from a
    collection of sub-distributions with randomly-selected means. This approach
    introduces more randomness into our sample than sampling from a normal distribution
    directly with the hope of emulating the biased randomness in human activity.

    Args:
        lo (float): Lower bound of the truncated normal distribution.
        hi (float): Upper bound of the truncated normal distribution.
        prefer_hi (bool, optional): Whether to prefer the upper bound rather than the
            lower. Defaults to False.
    Returns:
        float: A random float from a truncated normal distribution derived from a
            collection of sub-distributions with randomly-selected means.
    Examples:
        100,000 x `biased_trunc_norm_samp(0, 100)` graphed:
            src/img/explanatory/math_plots/biased-trunc-norm-samp-100k.png
    """
    # Select from two means, one at 1/3rd and one at 2/3 of the range. More could be
    # added later.
    means = [
        lo + (hi - lo) * (1 / 3),
        lo + (hi - lo) * (2 / 3),
    ]
    # Generate probabilities for each mean proportional to the index.
    p = [
        (i + 1) ** 2 / sum([(j + 1) ** 2 for j in range(len(means))])
        for i in range(len(means))
    ]
    if not prefer_hi:
        p = p[::-1]  # Reversed to prefer the lower bound.
    # Select a mean from the list with a probability proportional to the index.
    # With two means, we have an 80% preference one of them, and which one depends how
    # how `p` is ordered.
    index = np.random.choice(range(len(means)), p=p)
    mean = means[index]
    # Retrieve a sample from the truncated normal distribution.
    return trunc_norm_samp(lo, hi, mean=mean)


def trunc_chisquared_samp(df: int, min: float = 0, max: float = np.inf) -> float:
    """Generate a random sample from a Chi-squared distribution.

    Note that in a chi-squared distribution, the natural maximum value increases with
    the degrees of freedom. By imposing an upper limit (`max`) on the generated values,
    we may end up truncating the distribution, potentially causing an unnatural cutoff
    that affects the distribution's mean and variance. This truncation can lead to bias
    in the sample, as it may not accurately represent the underlying chi-squared
    distribution.

    Args:
        df (int): Degrees of freedom (approximately the average result).
        min (float, optional): Minimum allowable output. Defaults to 0.
        max (float, optional): Maximum allowable output. Defaults to `np.inf`.

    Returns:
        float: A random float from a Chi-squared distribution.

    Examples:
        For 100,000 samples of chisquared_sample(average = 25, min = 3):
        - Average = 24.98367264407156
        - Maximum = 67.39469215530804
        - Minimum = 3.636904524316633
        - Graphed: src/img/explanatory/math_plots/chi-square-samp-100k.png
    """
    if max is None:
        max = np.inf
    while True:
        x = np.random.chisquare(df)
        if x >= min and x <= max:
            return x


def random_chance(prob: float) -> bool:
    """Returns True or False given the odds of an event.

    Args:
        prob (float): The probability of the event occurring (between 0 and 1).

    Returns:
        True if the event happened, False otherwise.
    """
    if not isinstance(prob, float):
        raise TypeError("Probability must be a float")
    if prob < 0.000 or prob > 1.000:
        raise ValueError("Probability must be between 0 and 1")
    return secrets.SystemRandom().random() <= prob


def random_choice(choices: list) -> any:
    """Return a random choice from a list of choices.

    Args:
        choices (list): A list of choices to select from.

    Returns:
        any: A randomly selected choice from the list.
    """
    if not isinstance(choices, list):
        raise TypeError("Choices must be a list")
    if not choices:
        raise ValueError("Choices list cannot be empty")
    return secrets.SystemRandom().choice(choices)

if __name__ == "__main__":
    from matplotlib import pyplot as plt

    # Truncated normal distribution.
    samples = [trunc_norm_samp(lo=0, hi=100) for _ in range(100000)]
    print("Truncated normal distribution")
    print(f"Average output = {sum(samples) / len(samples)}")
    print(f"Maximum output = {max(samples)}")
    print(f"Minimum output = {min(samples)}")
    print()
    plt.hist(samples, bins=600)
    plt.title("Truncated normal distribution")
    plt.show()

    # Fancy normal distribution.
    samples = [biased_trunc_norm_samp(lo=0, hi=100) for _ in range(100000)]
    print("Truncated normal distribution")
    print(f"Average output = {sum(samples) / len(samples)}")
    print(f"Maximum output = {max(samples)}")
    print(f"Minimum output = {min(samples)}")
    print()
    plt.hist(samples, bins=600)
    plt.title("Fancy normal distribution")
    plt.show()

    # Chi-squared distribution.
    samples = [trunc_chisquared_samp(df=25) for _ in range(100000)]
    print("Chi-squared distribution")
    print(f"Average output = {sum(samples) / len(samples)}")
    print(f"Maximum output = {max(samples)}")
    print(f"Minimum output = {min(samples)}")
    plt.hist(samples, bins=600)
    plt.title("Chi-squared distribution")
    plt.show()
