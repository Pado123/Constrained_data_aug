import numpy as np
import scipy.stats as stats

# Define the possible distributions
possible_distributions = [
    'norm',       # Normal distribution
    'expon',      # Exponential distribution
    'uniform',    # Uniform distribution
    'triang',     # Triangular distribution
    'lognorm',    # Log-normal distribution
    'gamma'       # Gamma distribution
]

def find_best_fit_distribution(data):
    """
    Finds the best-fitting distribution for the given data.
    Args:
        data (array-like): The observed values.
    Returns:
        dict: Dictionary containing the best-fitting distribution, its name, and parameters.
    """
    best_fit = None
    best_stat = np.inf  # Lower is better for goodness-of-fit
    
    for dist_name in possible_distributions:
        dist = getattr(stats, dist_name)  # Get the distribution object
        try:
            # Fit the distribution to the data
            params = dist.fit(data)
            
            # Perform a goodness-of-fit test (Kolmogorov-Smirnov)
            ks_stat, _ = stats.kstest(data, dist_name, args=params)
            
            # Save if this distribution is better
            if ks_stat < best_stat:
                best_stat = ks_stat
                best_fit = {'name': dist_name, 'params': params}
        except Exception as e:
            # Skip distributions that fail to fit
            print(f"Skipping {dist_name}: {e}")
            continue
    
    return best_fit

def sample_time(distribution, n_samples=1):
    
    """
    Samples values from a given distribution.
    Args:
        distribution (dict): A dictionary with 'name' and 'params'.
        n_samples (int): Number of samples to generate.
    Returns:
        np.ndarray: Array of sampled values.
    """

    if distribution['name'] == 'fixed':
        return [distribution['value']]*n_samples
    
    dist = getattr(stats, distribution['name'])

    return dist.rvs(*distribution['params'], size=n_samples)